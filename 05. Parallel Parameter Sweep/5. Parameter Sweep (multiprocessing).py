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

#############################
#         PARAMETERS        #
#############################

# %% Set main parameters
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense() # Number of available parallel simulation license
duty_cycle_min = 0
duty_cycle_max = 0.9
numberOfPoints = 200    # Run 200 simulations


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

    BuckBoostConverter = DesignExamples.BuckBoostConverter()
   
    # Set duty cycle value
    PWM = BuckBoostConverter.Circuit.GetDeviceByName('C1')
    PWM.DutyCycle = duty_cycle

    # create job
    job = BuckBoostConverter.TransientAnalysis.NewJob()

    # Start job and log if error.
    status = job.Run()
    if str(status) != "OK": 
        print (job.Summary()[:-1])
        return; # ERROR 

    # Retrieve results
    signal = job.GetSignalByName('Rload - Voltage')
    t = np.array(signal.TimePoints)
    Vout = np.array(signal.DataPoints)

    # Average output voltage for t > 2ms
    indices = np.where(t >= 0.005)
    Vout = np.take(Vout, indices)

    # Save Voltage in the results
    calculated_voltages[simulation_number] = np.average(Vout)

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
    for _ in tqdm.tqdm(pool.imap(run_job_star, pool_args), total=len(pool_args)):
        pass

    # Plot curve and save image.
    print("3. Plot output voltage vs duty cycle...")
    calculated_voltages = list(calculated_voltages)
    fig, ax = plt.subplots()
    ax.set_title("Buck-Boost Converter Parametric Sweep")
    ax.set_ylabel('Vout (V)')
    ax.set_xlabel('Duty Cycle')
    ax.plot(duty_cycles, calculated_voltages)
    path = "buck_boost_parametric_sweep_" + datetime.now().strftime("%Y%m%d") + ".png"
    fig.savefig(path)
    plt.show()
