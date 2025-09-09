# Simulation for ZVS (Zero Voltage Switching) Loss Characterization
#
# This script runs SIMBA simulations using the SPICE model of an Infineon MOSFET
# under different current, voltage, and temperature conditions to export thermal
# data (conduction and switching losses).
#
# Simulations are run in parallel to optimize simulation time.
#
# Two-frequency method used:
#   E_total_f  = E_conduction + E_switching * f1
#   E_total_2f = E_conduction + E_switching * f2
# => Switching Loss  = E_total_2f - E_total_f
#    Conduction Loss = 2*E_total_f - E_total_2f

#%% Imports
import os
from aesim.simba import ProjectRepository, License
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import multiprocessing
import tqdm
import math


# Determine the number of available parallel simulation licenses
available_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense()


#%% Load the Simulation Project
script_directory = os.path.realpath(os.path.dirname(__file__))
project_file = os.path.join(script_directory, "zvs_characterization_infineonIMBG120R008M2H.jsimba")
fundamental_frequency = 100e3  # Fundamental switching frequency in Hz


#%% Define Data for Parametric Analysis
temperatures = [100, 175]  # Device temperatures in °C
dc_bus_voltage = 800       # DC bus voltage in V

# Load currents for simulations in A
load_currents = [10, 20, 30, 50, 70, 90, 130, 160, 180, 250, 310, 360]
if os.environ.get("SIMBA_SCRIPT_TEST"):  # Accelerate simulation in test environment
    load_currents = [10, 50, 130, 250]


#%% Helper: Rebase Signals onto a Unified Time Base
def rebase_signals(time1, signal1, time2, signal2, time3, signal3):
    """
    Interpolate three signals onto a unified time base.

    Returns
    -------
    unified_time : np.ndarray
    rebased_signal1, rebased_signal2, rebased_signal3 : np.ndarray
    """
    unified_time = np.array(sorted(set(time1).union(time2).union(time3)))

    interp_func1 = interp1d(time1, signal1, kind='linear', fill_value="extrapolate")
    interp_func2 = interp1d(time2, signal2, kind='linear', fill_value="extrapolate")
    interp_func3 = interp1d(time3, signal3, kind='linear', fill_value="extrapolate")

    rebased_signal1 = interp_func1(unified_time)
    rebased_signal2 = interp_func2(unified_time)
    rebased_signal3 = interp_func3(unified_time)

    return unified_time, rebased_signal1, rebased_signal2, rebased_signal3


#%% Function to Run a Single Simulation and Compute Energy-Related Values
def run_simulation(sim_index, temperature, load_current, switching_frequency, results_list, lock):
    """
    Run a simulation with specified parameters and compute energy losses.

    Parameters
    ----------
    sim_index : int
        Index where results will be stored in the shared list.
    temperature : float
        Device temperature in °C.
    load_current : float
        Load current in A.
    switching_frequency : float
        Switching frequency in Hz.
    results_list : multiprocessing.Manager().list
        Shared list to store the results.
    lock : multiprocessing.Manager().Lock
        Lock used to guard project loading.
    """
    # Load project under a lock (SIMBA project open is not process-safe)
    with lock:
        project = ProjectRepository(project_file)
    design = project.GetDesignByName('Design - Tc')

    # Configure simulation options
    design.TransientAnalysis.TimeStep = '5n'  # Time step of 5 nanoseconds
    simulation_end_time = 3 / fundamental_frequency  # Simulate for 3 periods of the fundamental frequency
    design.TransientAnalysis.EndTime = f'{simulation_end_time}'
    design.TransientAnalysis.NumberOfBasePeriodsSavedParameterEnabled = True
    design.TransientAnalysis.NumberOfBasePeriodsSaved = '1'  # Save data for 1 base period
    design.TransientAnalysis.BaseFrequencyParameterEnabled = True
    design.TransientAnalysis.BaseFrequency = f'{fundamental_frequency}'
    design.TransientAnalysis.CompressScopes = True  # Optimize performance

    # Set simulation parameters
    circuit = design.Circuit
    temperature_source = circuit.GetDeviceByName('Temp_source')  # Temperature source device
    temperature_source.Voltage = temperature
    circuit.SetVariableValue('iac', f'{load_current}')
    circuit.SetVariableValue('fsw', f'{switching_frequency}')
    circuit.SetVariableValue('udc', f'{dc_bus_voltage}')

    # Run the simulation
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK":
        print(job.Summary()[:-1])
        return

    # Retrieve signals
    vds = job.GetSignalByName('VDS_LS - Voltage')
    vgs = job.GetSignalByName('VGS_LS - Voltage')
    ils = job.GetSignalByName('i_LS - Current')

    vds_voltage, vds_time = np.array(vds.DataPoints), np.array(vds.TimePoints)
    vgs_voltage, vgs_time = np.array(vgs.DataPoints), np.array(vgs.TimePoints)
    mosfet_current, mosfet_current_time = np.array(ils.DataPoints), np.array(ils.TimePoints)

    # Rebase signals onto a common time base
    time_array, vds_r, i_r, vgs_r = rebase_signals(
        vds_time, vds_voltage,
        mosfet_current_time, mosfet_current,
        vgs_time, vgs_voltage,
    )

    # Instantaneous power and total energy loss over the simulated window
    instantaneous_power = vds_r * i_r
    total_energy_loss = float(np.trapz(instantaneous_power, time_array))

    # Switched current when Vgs < 3.2 V (threshold assumption)
    idxs = np.where(vgs_r < 3.2)[0]
    switched_current = float(i_r[idxs[0]]) if idxs.size else float('nan')

    # Conduction-phase metrics (start at 60% of one switching period)
    period = 1.0 / switching_frequency
    t_start = time_array[0] + 0.6 * period
    idx_start = int(np.searchsorted(time_array, t_start, side='right'))
    if idx_start >= len(time_array):
        idx_start = len(time_array) - 1

    if idx_start < len(time_array):
        local_segment = vds_r[idx_start:]
        if local_segment.size:
            local_max_idx = int(np.argmax(local_segment))
            i_max = idx_start + local_max_idx
            maximum_voltage = float(vds_r[i_max])
            forward_current = float(i_r[i_max])
            # Define a representative "delta voltage" and corresponding reverse current
            delta_voltage = float(vds_r[idx_start])
            reverse_current = float(i_r[idx_start])
        else:
            maximum_voltage = float('nan')
            forward_current = float('nan')
            delta_voltage = float('nan')
            reverse_current = float('nan')
    else:
        maximum_voltage = float('nan')
        forward_current = float('nan')
        delta_voltage = float('nan')
        reverse_current = float('nan')

    # Store results
    results_list[sim_index] = (
        float(temperature), float(load_current), float(switching_frequency),
        total_energy_loss, maximum_voltage, delta_voltage,
        switched_current, forward_current, reverse_current,
    )


def run_simulation_star(args):
    return run_simulation(*args)


#%% Main Execution
if __name__ == "__main__":
    print("Starting parametric analysis...")

    manager = multiprocessing.Manager()
    lock = manager.Lock()

    total_simulations = len(temperatures) * len(load_currents) * 2  # times 2 for f and 2f
    results = manager.list([None] * total_simulations)

    # Prepare simulation arguments
    sim_args = []
    sim_index = 0
    for T in temperatures:
        for I in load_currents:
            sim_args.append((sim_index, T, I, fundamental_frequency, results, lock)); sim_index += 1
            sim_args.append((sim_index, T, I, 2 * fundamental_frequency, results, lock)); sim_index += 1

    # Worker pool sized by SIMBA license and CPU count
    n_licenses = int(available_parallel_simulations) if available_parallel_simulations is not None else 1
    num_workers = max(1, min(n_licenses, multiprocessing.cpu_count()))
    pool = multiprocessing.Pool(processes=num_workers)

    for _ in tqdm.tqdm(pool.imap(run_simulation_star, sim_args), total=len(sim_args)):
        pass

    pool.close()
    pool.join()

    # Index results for easy lookup
    results_list = list(results)
    res_index = { (r[0], r[1], r[2]): r for r in results_list if r is not None }

    # Process and analyze results
    switching_losses_results = []
    conduction_losses_results = []

    for T in temperatures:
        switched_currents = []
        forward_currents = []
        reverse_currents = []
        maximum_voltages = []
        delta_voltages = []
        switching_losses = []
        conduction_losses = []

        for I in load_currents:
            r_f  = res_index.get((float(T), float(I), float(fundamental_frequency)))
            r_2f = res_index.get((float(T), float(I), float(2 * fundamental_frequency)))

            e_f  = r_f[3]  if r_f  else float('nan')
            e_2f = r_2f[3] if r_2f else float('nan')

            vmax = r_f[4]  if r_f  else float('nan')
            dV   = r_f[5]  if r_f  else float('nan')
            Isw  = r_f[6]  if r_f  else float('nan')
            Ifwd = r_f[7]  if r_f  else float('nan')
            Irev = r_f[8]  if r_f  else float('nan')

            sw_loss = e_2f - e_f if not (math.isnan(e_f) or math.isnan(e_2f)) else float('nan')
            cond_loss = 2 * e_f - e_2f if not (math.isnan(e_f) or math.isnan(e_2f)) else float('nan')
            if not math.isnan(sw_loss) and sw_loss < 0:
                print(f"Negative switching losses at T={T} °C, I={I} A")

            switched_currents.append(Isw)
            forward_currents.append(Ifwd)
            reverse_currents.append(Irev)
            maximum_voltages.append(vmax)
            delta_voltages.append(dV)
            switching_losses.append(sw_loss)
            conduction_losses.append(cond_loss)

        switching_losses_results.append({
            'temperature': T,
            'switched_currents': switched_currents,
            'maximum_voltages': maximum_voltages,
            'switching_losses': switching_losses,
        })
        conduction_losses_results.append({
            'temperature': T,
            'forward_currents': forward_currents,
            'reverse_currents': reverse_currents,
            'maximum_voltages': maximum_voltages,
            'delta_voltages': delta_voltages,
            'conduction_losses': conduction_losses,
        })

    if os.environ.get("SIMBA_SCRIPT_TEST"): exit() # Skip plotting in test environment

    # Save results to a text file (always write; plotting may be skipped in tests)
    results_file = os.path.join(script_directory, "loss_data.txt")
    with open(results_file, 'w') as f:
        f.write('Switching Losses:\n')
        f.write('Temperature (°C), Switched Current (A), Maximum Voltage (V), Switching Loss (J)\n')
        for result in switching_losses_results:
            temp = result['temperature']
            for scurr, mvolt, sloss in zip(result['switched_currents'], result['maximum_voltages'], result['switching_losses']):
                f.write(f'{temp}, {scurr}, {mvolt}, {sloss}\n')
            f.write('\n')

        f.write('\nConduction Losses:\n')
        f.write('Temperature (°C), Forward Current (A), Reverse Current (A), Maximum Voltage (V), Delta Voltage (V), Conduction Loss (J)\n')
        for result in conduction_losses_results:
            temp = result['temperature']
            for fcurr, rcurr, mvolt, dvolt, closs in zip(
                result['forward_currents'], result['reverse_currents'],
                result['maximum_voltages'], result['delta_voltages'],
                result['conduction_losses']):
                f.write(f'{temp}, {fcurr}, {rcurr}, {mvolt}, {dvolt}, {closs}\n')
            f.write('\n')

    # Plot (skip only in test env)
    is_test = bool(os.environ.get("SIMBA_SCRIPT_TEST"))
    if not is_test:
        fig, axs = plt.subplots(1, 2, figsize=(14, 6))
        line_styles = ['-', '--']

        # Plot Switching Losses
        for idx, result in enumerate(switching_losses_results):
            axs[0].plot(
                result['switched_currents'],
                result['switching_losses'],
                label=f'Temperature {result["temperature"]} °C',
                linestyle=line_styles[idx % len(line_styles)],
                linewidth=2,
                alpha=0.8,
            )
        axs[0].set_xlabel('Switched Current (A)')
        axs[0].set_ylabel('Switching Losses (J)')
        axs[0].set_title('Switching Losses vs. Switched Current')
        axs[0].legend()

        # Plot Conduction Losses
        for idx, result in enumerate(conduction_losses_results):
            axs[1].plot(
                load_currents,
                result['conduction_losses'],
                label=f'Temperature {result["temperature"]} °C',
                linestyle=line_styles[idx % len(line_styles)],
                linewidth=2,
                alpha=0.8,
            )
        axs[1].set_xlabel('Load Current (A)')
        axs[1].set_ylabel('Conduction Losses (J)')
        axs[1].set_title('Conduction Losses vs. Load Current')
        axs[1].legend()

        plt.tight_layout()

        plot_file = os.path.join(script_directory, "loss_data.png")
        fig.savefig(plot_file)
        plt.show()
