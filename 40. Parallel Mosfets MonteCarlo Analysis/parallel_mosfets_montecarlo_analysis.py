# Load modules
import os
import random
import multiprocessing
from tqdm import tqdm
from aesim.simba import ProjectRepository,License
from datetime import datetime
import pandas as pd

#############################
#         PARAMETERS        #
#############################
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense() # Number of available Parallel Simulation License

iterations = range(1000)
mosfet_index_list = ['11', '12', '13']
param = dict()
for mosfet_index in mosfet_index_list:
    param['Rdson'+ mosfet_index] = {'nominal': 60e-3, 'tolerance': 0.1}
    param['Rg'+ mosfet_index] = {'nominal': 20, 'tolerance': 0.1}

if os.environ.get("SIMBA_SCRIPT_TEST"): # To accelerate unit tests
    iterations = range(10)
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

def run_simulation(sim_number, manager_result_dict, lock):
    """
    Run SIMBA Simulation and place the results in "manager_result_dict"
    """   
    with lock:
        script_folder = os.path.realpath(os.path.dirname(__file__))
        file_path = os.path.join(script_folder, "parallel_mosfets_montecarlo_analysis.jsimba")
        project = ProjectRepository(file_path)
    design = project.GetDesignByName('Design 2')
    param_values = generate_random_values(param)
    for mosfet_index in mosfet_index_list:
        design.Circuit.GetDeviceByName('T'+mosfet_index).Ron = param_values['Rdson'+mosfet_index]
        design.Circuit.GetDeviceByName('T'+mosfet_index).Rgon = param_values['Rg'+mosfet_index]    
        design.Circuit.GetDeviceByName('T'+mosfet_index).Rgoff = param_values['Rg'+mosfet_index]    
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK": 
        print (job.Summary()[:-1])
    
    # manager_result_dict[sim_number] = []
    # for mosfet_index in mosfet_index_list:
    #     manager_result_dict[sim_number].append(param_values['Rdson'+mosfet_index])
    #     manager_result_dict[sim_number].append(param_values['Rg'+mosfet_index])
    #     manager_result_dict[sim_number].append(job.GetSignalByName('T'+mosfet_index +' - Average Total Losses (W)').DataPoints[-1])
    #     manager_result_dict[sim_number].append(job.GetSignalByName('T'+mosfet_index +' - Junction Temperature (°)').DataPoints[-1])
    manager_result_dict[sim_number] = [param_values['Rdson11'],
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
                                       job.GetSignalByName('T13 - Junction Temperature (°)').DataPoints[-1]]

def run_simulation_star(args):
    """
    Helper function used to call run_simulation with a single argument
    """
    return run_simulation(*args)

#############################
#         MAIN SCRIPT       #
#############################

if __name__ == "__main__": # Called only in main thread

    manager = multiprocessing.Manager()
    lock = manager.Lock()
    manager_result_dict = manager.dict()
    pool_args = [[iter, manager_result_dict, lock] for iter in iterations]
    pool = multiprocessing.Pool(number_of_parallel_simulations)
    for _ in tqdm(pool.imap(run_simulation_star, pool_args), total=len(pool_args)):
        pass
    
    # Store results in dedicated dictionnary
    res = dict()
    for mosfet_index in mosfet_index_list:
        res['Rdson'+mosfet_index] = []
        res['Rg'+mosfet_index] = []
        res['Losses'+mosfet_index] = []
        res['Tj'+mosfet_index] = []
    for item in manager_result_dict.items():
        for key, var_position in zip(res.keys(), range(len(res))):
            res[key].append(item[1][var_position])
    
    # Store results in dataframe to write it in a file
    df = pd.DataFrame(res)
    script_folder = os.path.realpath(os.path.dirname(__file__))
    filename = "montecarlo_parallel_mosfets_" + datetime.now().strftime("%Y-%m-%d")
    df.to_pickle(os.path.join(script_folder, filename + ".pkl"))