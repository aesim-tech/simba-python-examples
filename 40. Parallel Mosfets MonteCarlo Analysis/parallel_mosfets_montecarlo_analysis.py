# Load modules
import os
import random
import threading
from tqdm import tqdm
from aesim.simba import ProjectRepository, License
from datetime import datetime
import pandas as pd

#############################
#         PARAMETERS        #
#############################
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense()  # Number of available Parallel Simulation License

iterations = range(1000)
mosfet_index_list = ['11', '12', '13']
param = dict()
for mosfet_index in mosfet_index_list:
    param['Rdson' + mosfet_index] = {'nominal': 60e-3, 'tolerance': 0.1}
    param['Rg' + mosfet_index] = {'nominal': 20, 'tolerance': 0.1}

if os.environ.get("SIMBA_SCRIPT_TEST"):  # To accelerate unit tests
    iterations = range(10)

#############################
#       THREADING SETUP     #
#############################
# Limit concurrent simulations to available licenses
semaphore = threading.Semaphore(max(1, number_of_parallel_simulations))
# Be conservative opening the project file from multiple threads
project_open_lock = threading.Lock()

#############################
#           METHODS         #
#############################

def generate_random_values(param):
    """
    generate random values of param parameters given as a dictionnary

    :param: dictionnary of the different param elements (inductor, capacitor, resistor...)
    """
    param_values = {}
    for component, values in param.items():
        nominal_value = values['nominal']
        tolerance = values['tolerance']
        min_value = nominal_value - (tolerance * nominal_value)
        max_value = nominal_value + (tolerance * nominal_value)
        param_values[component] = random.uniform(min_value, max_value)
    return param_values


def run_simulation(sim_number, results_list):
    """
    Run SIMBA Simulation and place the results in results_list[sim_number]
    """
    with semaphore:
        # Load project (guard opening the file)
        with project_open_lock:
            script_folder = os.path.realpath(os.path.dirname(__file__))
            file_path = os.path.join(script_folder, "parallel_mosfets_montecarlo_analysis.jsimba")
            project = ProjectRepository(file_path)

        design = project.GetDesignByName('Design 2')

        # Draw random parameters
        param_values = generate_random_values(param)

        # Apply parameters to devices
        for mosfet_index in mosfet_index_list:
            design.Circuit.GetDeviceByName('T' + mosfet_index).Ron = param_values['Rdson' + mosfet_index]
            design.Circuit.GetDeviceByName('T' + mosfet_index).Rgon = param_values['Rg' + mosfet_index]
            design.Circuit.GetDeviceByName('T' + mosfet_index).Rgoff = param_values['Rg' + mosfet_index]

        # Run analysis
        job = design.TransientAnalysis.NewJob()
        status = job.Run()
        if str(status) != "OK":
            # Print summary and store a placeholder row (NaNs)
            print(job.Summary()[:-1])
            results_list[sim_number] = [param_values['Rdson11'],
                                        param_values['Rg11'],
                                        float('nan'), float('nan'),
                                        param_values['Rdson12'],
                                        param_values['Rg12'],
                                        float('nan'), float('nan'),
                                        param_values['Rdson13'],
                                        param_values['Rg13'],
                                        float('nan'), float('nan')]
            return

        # Pack result for T11/T12/T13 in the exact order expected downstream
        results_list[sim_number] = [
            param_values['Rdson11'],
            param_values['Rg11'],
            job.GetSignalByName('T11 - Average Total Losses (W)').DataPoints[-1],
            job.GetSignalByName('T11 - Junction Temperature (°)').DataPoints[-1],
            param_values['Rdson12'],
            param_values['Rg12'],
            job.GetSignalByName('T12 - Average Total Losses (W)').DataPoints[-1],
            job.GetSignalByName('T12 - Junction Temperature (°)').DataPoints[-1],
            param_values['Rdson13'],
            param_values['Rg13'],
            job.GetSignalByName('T13 - Average Total Losses (W)').DataPoints[-1],
            job.GetSignalByName('T13 - Junction Temperature (°)').DataPoints[-1],
        ]


#############################
#         MAIN SCRIPT       #
#############################

if __name__ == "__main__":  # Called only in main thread
    # Pre-size results for O(1) thread-safe index writes
    num_runs = len(iterations)
    results = [None] * num_runs

    # Launch threads (one per planned simulation), concurrency limited by semaphore
    threads = []
    for sim_number in iterations:
        t = threading.Thread(target=run_simulation, args=(sim_number, results))
        t.start()
        threads.append(t)

    # Progress bar while joining
    for t in tqdm(threads, total=len(threads)):
        t.join()

    # Build column-wise dict in the same insertion order as before
    res = dict()
    for mosfet_index in mosfet_index_list:
        res['Rdson' + mosfet_index] = []
        res['Rg' + mosfet_index] = []
        res['Losses' + mosfet_index] = []
        res['Tj' + mosfet_index] = []

    # Fold row-wise results into columns
    for row in results:
        if row is None:
            # In case of unexpected thread failure, keep placeholders
            row = [float('nan')] * 12
        for key, var_position in zip(res.keys(), range(len(res))):
            res[key].append(row[var_position])

    # Store results in dataframe to write it in a file
    df = pd.DataFrame(res)
    script_folder = os.path.realpath(os.path.dirname(__file__))
    filename = "montecarlo_parallel_mosfets_" + datetime.now().strftime("%Y-%m-%d")
    df.to_pickle(os.path.join(script_folder, filename + ".pkl"))