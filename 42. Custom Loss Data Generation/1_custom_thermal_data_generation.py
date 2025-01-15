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
from aesim.simba import ProjectRepository, License
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from datetime import datetime
import multiprocessing
import tqdm

# Determine the number of available parallel simulation licenses
available_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense()

#%% Load the Simulation Project
script_directory = os.path.realpath(os.path.dirname(__file__))
project_file = os.path.join(script_directory, "zvs_characterization_infineonIMBG120R008M2H.jsimba")
project = ProjectRepository(project_file)
design = project.GetDesignByName('Design - Tc')

#%% Set Global Variables and Simulation Parameters
circuit = design.Circuit
fundamental_frequency = 100e3  # Fundamental switching frequency in Hz

#%% Configure Simulation Options
design.TransientAnalysis.TimeStep = '5n'  # Time step of 2 nanoseconds
simulation_end_time = 3 / fundamental_frequency  # Simulate for 3 periods
design.TransientAnalysis.EndTime = f'{simulation_end_time}'
design.TransientAnalysis.NumberOfBasePeriodsSavedParameterEnabled = True
design.TransientAnalysis.NumberOfBasePeriodsSaved = '1'  # Save data for 1 base period
design.TransientAnalysis.BaseFrequencyParameterEnabled = True
design.TransientAnalysis.BaseFrequency = f'{fundamental_frequency}'
design.TransientAnalysis.CompressScopes = True  # Enable compressed scopes to optimize performance

#%% Define Data for Parametric Analysis
temperatures = [100, 175]  # Device temperatures in degrees Celsius
dc_bus_voltage = 800  # DC bus voltage in volts

# Load currents for simulations in amperes
load_currents = [10, 20, 30, 50, 70, 90, 130, 160, 180, 250, 310, 360]

#%% Retrieve Devices from the Circuit
temperature_source = circuit.GetDeviceByName('Temp_source')  # Temperature source device

#%% Helper Function to Rebase Signals onto a Unified Time Base
def rebase_signals(time1, signal1, time2, signal2, time3, signal3):
    """
    Rebase three signals onto a unified time base by interpolating them.

    Parameters:
    - time1, signal1: Time points and data points of the first signal.
    - time2, signal2: Time points and data points of the second signal.
    - time3, signal3: Time points and data points of the third signal.

    Returns:
    - unified_time: The unified time array.
    - rebased_signal1, rebased_signal2, rebased_signal3: The signals interpolated onto the unified time base.
    """
    # Create a unified set of time points
    unified_time = sorted(set(time1).union(time2).union(time3))
    
    # Interpolate the signals to the unified time points
    interp_func1 = interp1d(time1, signal1, kind='linear', fill_value="extrapolate")
    interp_func2 = interp1d(time2, signal2, kind='linear', fill_value="extrapolate")
    interp_func3 = interp1d(time3, signal3, kind='linear', fill_value="extrapolate")
    
    # Get interpolated signal values at the unified time points
    rebased_signal1 = interp_func1(unified_time)
    rebased_signal2 = interp_func2(unified_time)
    rebased_signal3 = interp_func3(unified_time)
    
    return np.array(unified_time), np.array(rebased_signal1), np.array(rebased_signal2), np.array(rebased_signal3)

#%% Function to Run Simulations and Compute Energy Losses
def run_simulation(sim_index, temperature, load_current, switching_frequency, results_list):
    """
    Run a simulation with specified parameters and compute energy losses.

    Parameters:
    - sim_index: Index of the simulation (used to store results).
    - temperature: Device temperature in degrees Celsius.
    - load_current: Load current in amperes.
    - switching_frequency: Switching frequency in Hz.
    - results_list: Shared list to store the results.

    Returns:
    - None
    """
    # Set simulation parameters
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
    
    # Retrieve signals from the simulation
    vds_voltage = job.GetSignalByName('VDS_LS - Voltage').DataPoints
    vds_time = job.GetSignalByName('VDS_LS - Voltage').TimePoints
    vgs_voltage = job.GetSignalByName('VGS_LS - Voltage').DataPoints
    vgs_time = job.GetSignalByName('VGS_LS - Voltage').TimePoints
    mosfet_current = job.GetSignalByName('i_LS - Current').DataPoints
    mosfet_current_time = job.GetSignalByName('i_LS - Current').TimePoints
    
    # Rebase the signals onto a common time base
    time_array, rebased_vds_voltage, rebased_mosfet_current, rebased_vgs_voltage = rebase_signals(
        vds_time, vds_voltage,
        mosfet_current_time, mosfet_current,
        vgs_time, vgs_voltage)
    
    # Calculate instantaneous power and total energy loss over the simulation period
    instantaneous_power = rebased_vds_voltage * rebased_mosfet_current
    total_energy_loss = np.trapz(instantaneous_power, time_array)
    
    # Extract the switched current when Vgs < 3.2V (assumed threshold voltage)
    switched_current = rebased_mosfet_current[rebased_vgs_voltage < 3.2][0]
    
    # Calculate maximum voltage across the MOSFET during the conduction phase
    # We consider the conduction phase starting after 60% of the period
    conduction_phase_start_time = time_array[0] + 0.6 / switching_frequency  # Time at 60% of the period
    index_conduction_start = next(i for i, t in enumerate(time_array) if t > conduction_phase_start_time)
    maximum_voltage = max(rebased_vds_voltage[index_conduction_start:])
    forward_current = rebased_mosfet_current[rebased_vds_voltage == maximum_voltage]
    
    # Calculate delta voltage during turn-off phase
    # We consider the voltage at a specific time point
    target_time = time_array[0] + 0.5155e-05  # Specific time in seconds
    if target_time < time_array[0] or target_time > time_array[-1]:
        print(f"Target time {target_time} is out of the range of the time array.")
        return
    
    delta_voltage = rebased_vds_voltage[time_array > conduction_phase_start_time][0]
    reverse_current = rebased_mosfet_current[rebased_vds_voltage == delta_voltage]
    
    # Store the results
    results_list[sim_index] = (
        temperature, load_current, switching_frequency, total_energy_loss,
        maximum_voltage, delta_voltage, switched_current, forward_current, reverse_current)

# Helper function for multiprocessing
def run_simulation_star(args):
    return run_simulation(*args)

#%% Main Execution: Run Simulations in Parallel and Process Results
if __name__ == "__main__":
    print("Starting parametric analysis...")
    # Use a manager to handle shared data structures between processes
    manager = multiprocessing.Manager()
    # Shared list to store results; pre-initialize with None
    total_simulations = len(temperatures) * len(load_currents) * 2  # Multiply by 2 for two frequencies
    results = manager.list([None] * total_simulations)
    simulation_args = []
    
    sim_index = 0
    # Prepare the list of arguments for each simulation
    for temperature in temperatures:
        for load_current in load_currents:
            # Simulations at fundamental frequency
            simulation_args.append((sim_index, temperature, load_current, fundamental_frequency, results))
            sim_index += 1
            # Simulations at twice the fundamental frequency
            simulation_args.append((sim_index, temperature, load_current, 2 * fundamental_frequency, results))
            sim_index += 1
    
    # Determine the number of worker processes
    num_workers = min(available_parallel_simulations, multiprocessing.cpu_count())
    pool = multiprocessing.Pool(processes=num_workers)
    
    # Run the simulations in parallel with a progress bar
    for _ in tqdm.tqdm(pool.imap(run_simulation_star, simulation_args), total=len(simulation_args)):
        pass
    
    pool.close()
    pool.join()
    
    #%% Process and Analyze Results
    switching_losses_results = []
    conduction_losses_results = []
    
    for temperature in temperatures:
        currents = []
        switching_losses = []
        conduction_losses = []
        switched_currents = []
        forward_currents = []
        reverse_currents = []
        maximum_voltages = []
        delta_voltages = []
        
        for load_current in load_currents:
            # Extract total energy losses at fundamental and double frequencies
            energy_loss_fundamental = next(res[3] for res in results if res[0] == temperature and res[1] == load_current and res[2] == fundamental_frequency)
            energy_loss_double = next(res[3] for res in results if res[0] == temperature and res[1] == load_current and res[2] == 2 * fundamental_frequency)
            
            # Extract maximum voltage and delta voltage at fundamental frequency
            maximum_voltage = next(res[4] for res in results if res[0] == temperature and res[1] == load_current and res[2] == fundamental_frequency)
            delta_voltage = next(res[5] for res in results if res[0] == temperature and res[1] == load_current and res[2] == fundamental_frequency)
            
            # Get switched, forward, and reverse currents at fundamental frequency
            switched_current = next(res[6] for res in results if res[0] == temperature and res[1] == load_current and res[2] == fundamental_frequency)
            forward_current = next(res[7] for res in results if res[0] == temperature and res[1] == load_current and res[2] == fundamental_frequency)
            reverse_current = next(res[8] for res in results if res[0] == temperature and res[1] == load_current and res[2] == fundamental_frequency)
            
            currents.append(load_current)
            switched_currents.append(switched_current)
            forward_currents.append(forward_current)
            reverse_currents.append(reverse_current)
            maximum_voltages.append(maximum_voltage)
            delta_voltages.append(delta_voltage)
            
            # swiching and conduction losses calculated using the two frequency method
            switching_loss = energy_loss_double - energy_loss_fundamental
            conduction_loss = 2 * energy_loss_fundamental - energy_loss_double
            
            if switching_loss < 0:
                print(f"Negative switching losses at temperature {temperature} °C and load current {load_current} A")
            
            switching_losses.append(switching_loss)
            conduction_losses.append(conduction_loss)
        
        # Store the results for the current temperature
        switching_losses_results.append({
            'temperature': temperature,
            'switched_currents': switched_currents,
            'maximum_voltages': maximum_voltages,
            'switching_losses': switching_losses
        })
        conduction_losses_results.append({
            'temperature': temperature,
            'forward_currents': forward_currents,
            'reverse_currents': reverse_currents,
            'maximum_voltages': maximum_voltages,
            'delta_voltages': delta_voltages,
            'conduction_losses': conduction_losses
        })
    
    # Save results to a text file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(script_directory, f"loss_data.txt")
    
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
    
    #%% Plot Results
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
            alpha=0.8
        )
    axs[0].set_xlabel('Switched Current (A)')
    axs[0].set_ylabel('Switching Losses (J)')
    axs[0].set_title('Switching Losses vs. Switched Current')
    axs[0].legend()
    
    # Plot Conduction Losses
    for idx, result in enumerate(conduction_losses_results):
        axs[1].plot(
            currents,  # Load currents
            result['conduction_losses'],
            label=f'Temperature {result["temperature"]} °C',
            linestyle=line_styles[idx % len(line_styles)],
            linewidth=2,
            alpha=0.8
        )
    axs[1].set_xlabel('Load Current (A)')
    axs[1].set_ylabel('Conduction Losses (J)')
    axs[1].set_title('Conduction Losses vs. Load Current')
    axs[1].legend()
    
    plt.tight_layout()
    
    # Save the plot as an image file
    plot_file = os.path.join(script_directory, f"loss_data.png")
    fig.savefig(plot_file)
    plt.show()