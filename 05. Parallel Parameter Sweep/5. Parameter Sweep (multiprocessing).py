"""
This simple scripts shows how the SIMBA Python Library can be used to run calculations on parallel processes and accelerate simulation.

Make sure to run 'pip install -r requirements.txt' to ensure you have the required packages.
"""
# %% Load required modules
from aesim.simba import DesignExamples, License
from datetime import datetime
import multiprocessing, tqdm #tqdm is for the progress bar
import matplotlib.pyplot as plt
import numpy as np
import os

#############################
#         PARAMETERS        #
#############################

# %% Set main parameters
number_of_parallel_simulations =  License.NumberOfAvailableParallelSimulationLicense() # Number of available parallel simulation license

duty_cycle_min = 0
duty_cycle_max = 0.9
numberOfPoints = 200    # Run 200 simulations

# Reduce simulation points for testing
if os.environ.get("SIMBA_SCRIPT_TEST"): # Accelerate simulation in test environment.
    numberOfPoints = 10


#############################
#           METHODS         #
#############################

# %% Define the functions to be run in parallel
def run_job(simulation_number, duty_cycle, calculated_voltages):
    """
    This thread-safe function:
    - Loads the buck-boost design example
    - Changes the duty cycle value
    - Runs the simulation
    - Calculates the output voltage and store it in calculated_voltages

    Args:
        simulation_number (int): number of the current run
        duty_cycle (float): duty-cycle to
        calculated_voltages ([float]): thread-safe list used to store results
    """
    try:
        BuckBoostConverter = DesignExamples.BuckBoostConverter()

        # Set duty cycle value
        PWM = BuckBoostConverter.Circuit.GetDeviceByName('C1')
        PWM.DutyCycle = duty_cycle

        # create job
        job = BuckBoostConverter.TransientAnalysis.NewJob()

        # Start job and log if error.
        status = job.Run()
        if str(status) != "OK":
            error_msg = f"Simulation {simulation_number} failed with status: {status}\n{job.Summary()[:-1]}"
            print(error_msg)
            calculated_voltages[simulation_number] = float('nan')  # Mark as failed
            return

        # Retrieve results
        signal = job.GetSignalByName('Rload - Voltage')
        t = np.array(signal.TimePoints)
        Vout = np.array(signal.DataPoints)

        # Average output voltage for t > 2ms
        indices = np.where(t >= 0.005)
        Vout = np.take(Vout, indices)

        # Save Voltage in the results
        calculated_voltages[simulation_number] = np.average(Vout)

    except Exception as e:
        error_msg = f"Exception in simulation {simulation_number} (duty_cycle={duty_cycle}): {type(e).__name__}: {str(e)}"
        print(error_msg)
        calculated_voltages[simulation_number] = float('nan')  # Mark as failed
        return

def run_job_star(args):
    """
    Helper function used to call run_job with a single argument
    """
    return run_job(*args)

#############################
#         MAIN SCRIPT       #
#############################

# %% Create the jobs and start the calculatiom 
if __name__ == "__main__": # Called only in main thread
    print("1. Initialization")
    duty_cycles = np.arange(duty_cycle_min, duty_cycle_max, duty_cycle_max / numberOfPoints).tolist()

    manager = multiprocessing.Manager()
    calculated_voltages = manager.list(range(len(duty_cycles)))
    pool_args = [[i, duty_cycles[i], calculated_voltages] for i in range(numberOfPoints)]

    # Create and start the processing pool
    print("2. Running...")
    pool = multiprocessing.Pool(number_of_parallel_simulations)

    # Use imap_unordered for better error handling and progress tracking
    results = []
    try:
        for result in tqdm.tqdm(pool.imap(run_job_star, pool_args), total=len(pool_args)):
            results.append(result)
    except Exception as e:
        print(f"Pool execution error: {type(e).__name__}: {str(e)}")
        pool.terminate()
        pool.join()
        raise
    finally:
        pool.close()
        pool.join()

    # Plot curve and save image.
    print("3. Plot output voltage vs duty cycle...")
    calculated_voltages = list(calculated_voltages)

    # Check for failed simulations and report them
    failed_count = sum(1 for v in calculated_voltages if isinstance(v, float) and str(v) == 'nan')
    if failed_count > 0:
        print(f"Warning: {failed_count} out of {len(calculated_voltages)} simulations failed.")
        print("Failed simulations will be excluded from the plot.")

    # Filter out NaN values for plotting
    valid_indices = [i for i, v in enumerate(calculated_voltages) if not (isinstance(v, float) and str(v) == 'nan')]
    valid_duty_cycles = [duty_cycles[i] for i in valid_indices]
    valid_voltages = [calculated_voltages[i] for i in valid_indices]

    if len(valid_duty_cycles) == 0:
        print("Error: All simulations failed. Cannot create plot.")
        exit(1)  # Exit the script with error code

    fig, ax = plt.subplots()
    ax.set_title("Buck-Boost Converter Parametric Sweep")
    ax.set_ylabel('Vout (V)')
    ax.set_xlabel('Duty Cycle')
    ax.plot(valid_duty_cycles, valid_voltages, 'b-', marker='o', markersize=2)
    ax.grid(True, alpha=0.3)

    path = "buck_boost_parametric_sweep_" + datetime.now().strftime("%Y%m%d") + ".png"
    fig.savefig(path)
    print(f"Plot saved as: {path}")
    plt.show()
