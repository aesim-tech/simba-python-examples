"""
This simple scripts shows how the SIMBA Python Library can be used to run calculations on parallel threads and accelerate simulation.

Make sure to run 'pip install -r requirements.txt' to ensure you have the required packages.
"""
# %% Load required modules
from aesim.simba import DesignExamples, License
from datetime import datetime
import threading, tqdm  # tqdm is for the progress bar
import matplotlib.pyplot as plt
import numpy as np

number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense() # Number of available parallel simulation license
semaphore = threading.Semaphore(number_of_parallel_simulations)

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
    with semaphore:
        BuckBoostConverter = DesignExamples.BuckBoostConverter()

        # Set duty cycle value
        PWM = BuckBoostConverter.Circuit.GetDeviceByName('C1')
        PWM.DutyCycle = duty_cycle

        # create job
        job = BuckBoostConverter.TransientAnalysis.NewJob()

        # Start job and log if error.
        job.Run()
        status = job.Run()
        if str(status) != "OK":
            print(job.Summary()[:-1])
            return  # ERROR

        # Retrieve results
        t = np.array(job.TimePoints)
        Vout = np.array(job.GetSignalByName('Rload - Voltage').DataPoints)

        # Average output voltage for t > 2ms
        indices = np.where(t >= 0.005)
        Vout = np.take(Vout, indices)

        # Save Voltage in the results
        calculated_voltages[simulation_number] = np.average(Vout)


#############################
#         MAIN SCRIPT       #
#############################

# %% Create the jobs and start the calculatiom
if __name__ == "__main__":  # Called only in main thread.
    print("1. Initialization")
    numberOfPoints = 200  # Run 200 simulations
    duty_cycles = np.arange(0.00, 0.9, 0.9 / numberOfPoints)
    calculated_voltages = [None] * len(duty_cycles)
    threads = []

    for i in range(len(duty_cycles)):
        t = threading.Thread(target=run_job, args=(i, duty_cycles[i], calculated_voltages))
        threads.append(t)
        t.start()

    print("2. Running...")
    for t in tqdm.tqdm(threads):
        t.join()

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
