# Simulation for ZVS (Zero Voltage Switching) Loss Characterization

# This script runs SIMBA simulations using the SPICE model of an Infineon MOSFET under different current,
# voltage, and temperature conditions to export thermal data (conduction and switching losses).

# Simulations are run in parallel to optimize simulation time

# Key Steps:
# 1. Define temperature and load current ranges.
# 2. Rebase voltage/current signals onto a unified time base for accurate calculations.
# 3. Compute switching and conduction losses.
# 4. Save results and visualize them.

# Note: Switching and conduction losses are calculated using the two-frequency method:
#   The total energy loss E_total = E_conduction + E_switching
#   Assuming conduction losses are independent of frequency and switching losses are proportional to frequency,
#   we can write:
#       E_total_fundamental = E_conduction + E_switching * f1
#       E_total_double = E_conduction + E_switching * f2
#   Therefore:
#       Switching Losses = (E_total_double - E_total_fundamental)
#       Conduction Losses = (2 * E_total_fundamental) - E_total_double

#%% Import Necessary Modules
import os
import threading
from aesim.simba import ProjectRepository, License
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from datetime import datetime
import tqdm
import math

# Determine the number of available parallel simulation licenses
available_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense()
semaphore = threading.Semaphore(max(1, available_parallel_simulations))
project_open_lock = threading.Lock()  # conservative guard when opening the .jsimba

#%% Load the Simulation Project (path only; open per-thread)
script_directory = os.path.realpath(os.path.dirname(__file__))
project_file = os.path.join(script_directory, "zvs_characterization_infineonIMBG120R008M2H.jsimba")

#%% Global parameters (unchanged)
fundamental_frequency = 100e3  # Hz

# Design-wide analysis options from the original script
TIME_STEP = '5n'
END_TIME_FOR_ALL_RUNS = 3 / fundamental_frequency  # Always 3 periods of 100 kHz (30 µs)
BASE_FREQ_FOR_ALL_RUNS = fundamental_frequency
SAVE_BASE_PERIODS = '1'

#%% Define data for parametric analysis
temperatures = [100, 175]   # °C
dc_bus_voltage = 800        # V
load_currents = [10, 20, 30, 50, 70, 90, 130, 160, 180, 250, 310, 360]  # A

#%% Helper: rebase signals onto a unified time base
def rebase_signals(time1, signal1, time2, signal2, time3, signal3):
    unified_time = sorted(set(time1).union(time2).union(time3))
    f1 = interp1d(time1, signal1, kind='linear', fill_value="extrapolate")
    f2 = interp1d(time2, signal2, kind='linear', fill_value="extrapolate")
    f3 = interp1d(time3, signal3, kind='linear', fill_value="extrapolate")
    s1 = f1(unified_time)
    s2 = f2(unified_time)
    s3 = f3(unified_time)
    return np.array(unified_time), np.array(s1), np.array(s2), np.array(s3)

#%% Thread target
def run_simulation(sim_index, temperature, load_current, switching_frequency, results_list):
    """
    Writes a tuple into results_list[sim_index]:
      (temperature, load_current, switching_frequency,
       total_energy_loss, maximum_voltage, delta_voltage,
       switched_current, forward_current, reverse_current)
    """
    with semaphore:
        try:
            # Open project and fetch design (new instance per thread)
            with project_open_lock:
                project = ProjectRepository(project_file)
            design = project.GetDesignByName('Design - Tc')

            # --- IMPORTANT: replicate original global analysis settings ---
            ta = design.TransientAnalysis
            ta.TimeStep = TIME_STEP
            ta.EndTime = f'{END_TIME_FOR_ALL_RUNS}'
            ta.NumberOfBasePeriodsSavedParameterEnabled = True
            ta.NumberOfBasePeriodsSaved = SAVE_BASE_PERIODS
            ta.BaseFrequencyParameterEnabled = True
            ta.BaseFrequency = f'{BASE_FREQ_FOR_ALL_RUNS}'
            ta.CompressScopes = True
            # -------------------------------------------------------------

            circuit = design.Circuit
            temperature_source = circuit.GetDeviceByName('Temp_source')

            # Per-run variables (as in original)
            temperature_source.Voltage = temperature
            circuit.SetVariableValue('iac', f'{load_current}')
            circuit.SetVariableValue('fsw', f'{switching_frequency}')
            circuit.SetVariableValue('udc', f'{dc_bus_voltage}')

            # Run
            job = ta.NewJob()
            status = job.Run()
            if str(status) != "OK":
                print(job.Summary()[:-1])
                results_list[sim_index] = (
                    temperature, load_current, switching_frequency,
                    float('nan'), float('nan'), float('nan'),
                    float('nan'), float('nan'), float('nan')
                )
                return

            # Signals
            vds_sig = job.GetSignalByName('VDS_LS - Voltage')
            vgs_sig = job.GetSignalByName('VGS_LS - Voltage')
            i_sig   = job.GetSignalByName('i_LS - Current')

            vds_v = np.array(vds_sig.DataPoints); vds_t = np.array(vds_sig.TimePoints)
            vgs_v = np.array(vgs_sig.DataPoints); vgs_t = np.array(vgs_sig.TimePoints)
            i_ls  = np.array(i_sig.DataPoints);   i_t   = np.array(i_sig.TimePoints)

            # Rebase to unified time
            t, vds, irebased, vgs = rebase_signals(vds_t, vds_v, i_t, i_ls, vgs_t, vgs_v)

            # Energy integration over the (unchanged) 30 µs window
            p = vds * irebased
            total_energy_loss = float(np.trapezoid(p, t))

            # Switched current at Vgs < 3.2 V (first occurrence)
            try:
                idx_sw = np.flatnonzero(vgs < 3.2)[0]
                switched_current = float(irebased[idx_sw])
            except Exception:
                switched_current = float('nan')

            # Conduction phase: after 60% of *current run* period (this matches your original logic)
            period = 1.0 / switching_frequency
            t_cond_start = t[0] + 0.6 * period
            try:
                idx_cond_start = int(np.flatnonzero(t > t_cond_start)[0])
            except Exception:
                idx_cond_start = 0

            try:
                seg = vds[idx_cond_start:]
                maximum_voltage = float(np.max(seg))
                mask_max = (vds == maximum_voltage)
                fwd_vals = irebased[mask_max]
                forward_current = float(fwd_vals[0]) if fwd_vals.size else float('nan')
            except Exception:
                maximum_voltage = float('nan')
                forward_current = float('nan')

            # Delta voltage (per original: first sample after conduction start)
            try:
                delta_voltage = float(vds[t > t_cond_start][0])
            except Exception:
                delta_voltage = float('nan')

            try:
                mask_delta = (vds == delta_voltage)
                rev_vals = irebased[mask_delta]
                reverse_current = float(rev_vals[0]) if rev_vals.size else float('nan')
            except Exception:
                reverse_current = float('nan')

            # Store
            results_list[sim_index] = (
                temperature, load_current, switching_frequency, total_energy_loss,
                maximum_voltage, delta_voltage, switched_current, forward_current, reverse_current
            )

        except Exception as e:
            print(f"Simulation error at T={temperature}°C, I={load_current}A, f={switching_frequency}Hz: {type(e).__name__}: {e}")
            results_list[sim_index] = (
                temperature, load_current, switching_frequency,
                float('nan'), float('nan'), float('nan'),
                float('nan'), float('nan'), float('nan')
            )

#%% Main Execution
if __name__ == "__main__":
    print("Starting parametric analysis...")

    total_simulations = len(temperatures) * len(load_currents) * 2  # f and 2f
    results = [None] * total_simulations

    sim_args = []
    sim_index = 0
    for T in temperatures:
        for I in load_currents:
            sim_args.append((sim_index, T, I, fundamental_frequency, results)); sim_index += 1
            sim_args.append((sim_index, T, I, 2 * fundamental_frequency, results)); sim_index += 1

    threads = []
    for args in sim_args:
        t = threading.Thread(target=run_simulation, args=args)
        t.start()
        threads.append(t)

    for t in tqdm.tqdm(threads, total=len(threads)):
        t.join()

    # ---- Post-processing identical to your original (unchanged) ----
    switching_losses_results = []
    conduction_losses_results = []

    for T in temperatures:
        currents = []
        switching_losses = []
        conduction_losses = []
        switched_currents = []
        forward_currents = []
        reverse_currents = []
        maximum_voltages = []
        delta_voltages = []

        for I in load_currents:
            e_f = next((r[3] for r in results if r and r[0] == T and r[1] == I and r[2] == fundamental_frequency), float('nan'))
            e_2f = next((r[3] for r in results if r and r[0] == T and r[1] == I and r[2] == 2 * fundamental_frequency), float('nan'))

            vmax = next((r[4] for r in results if r and r[0] == T and r[1] == I and r[2] == fundamental_frequency), float('nan'))
            dV   = next((r[5] for r in results if r and r[0] == T and r[1] == I and r[2] == fundamental_frequency), float('nan'))
            Isw  = next((r[6] for r in results if r and r[0] == T and r[1] == I and r[2] == fundamental_frequency), float('nan'))
            Ifwd = next((r[7] for r in results if r and r[0] == T and r[1] == I and r[2] == fundamental_frequency), float('nan'))
            Irev = next((r[8] for r in results if r and r[0] == T and r[1] == I and r[2] == fundamental_frequency), float('nan'))

            currents.append(I)
            switched_currents.append(Isw)
            forward_currents.append(Ifwd)
            reverse_currents.append(Irev)
            maximum_voltages.append(vmax)
            delta_voltages.append(dV)

            sw_loss = e_2f - e_f
            cond_loss = 2 * e_f - e_2f
            if not math.isnan(sw_loss) and sw_loss < 0:
                print(f"Negative switching losses at T={T} °C, I={I} A")

            switching_losses.append(sw_loss)
            conduction_losses.append(cond_loss)

        switching_losses_results.append({
            'temperature': T,
            'switched_currents': switched_currents,
            'maximum_voltages': maximum_voltages,
            'switching_losses': switching_losses
        })
        conduction_losses_results.append({
            'temperature': T,
            'forward_currents': forward_currents,
            'reverse_currents': reverse_currents,
            'maximum_voltages': maximum_voltages,
            'delta_voltages': delta_voltages,
            'conduction_losses': conduction_losses
        })

    # Save text + plot (same filenames as before)
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
                result['conduction_losses']
            ):
                f.write(f'{temp}, {fcurr}, {rcurr}, {mvolt}, {dvolt}, {closs}\n')
            f.write('\n')

    fig, axs = plt.subplots(1, 2, figsize=(14, 6))
    line_styles = ['-', '--']
    for idx, result in enumerate(switching_losses_results):
        axs[0].plot(result['switched_currents'], result['switching_losses'],
                    label=f'Temperature {result["temperature"]} °C',
                    linestyle=line_styles[idx % len(line_styles)], linewidth=2, alpha=0.8)
    axs[0].set_xlabel('Switched Current (A)')
    axs[0].set_ylabel('Switching Losses (J)')
    axs[0].set_title('Switching Losses vs. Switched Current')
    axs[0].legend()

    for idx, result in enumerate(conduction_losses_results):
        axs[1].plot(load_currents, result['conduction_losses'],
                    label=f'Temperature {result["temperature"]} °C',
                    linestyle=line_styles[idx % len(line_styles)], linewidth=2, alpha=0.8)
    axs[1].set_xlabel('Load Current (A)')
    axs[1].set_ylabel('Conduction Losses (J)')
    axs[1].set_title('Conduction Losses vs. Load Current')
    axs[1].legend()

    plt.tight_layout()
    plot_file = os.path.join(script_directory, "loss_data.png")
    fig.savefig(plot_file)
    plt.show()