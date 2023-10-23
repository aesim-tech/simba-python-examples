# Load modules
import os
import random
import multiprocessing
from tqdm import tqdm
from aesim.simba import ProjectRepository
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd


#############################
#         PARAMETERS        #
#############################

iterations = range(1000)
param = {
        'Rdson11' : {'nominal': 60e-3, 'tolerance': 0.1},
        'Rdson12' : {'nominal': 60e-3, 'tolerance': 0.1},
        'Rg11' : {'nominal': 20, 'tolerance': 0.1},
        'Rg12' : {'nominal': 20, 'tolerance': 0.1},
        }


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

    :param: id_ref, d-axis current refereance[A]
    :param: iq_ref, q-axis current refereance[A] 
    """   
    with lock:
        script_folder = os.path.realpath(os.path.dirname(__file__))
        file_path = os.path.join(script_folder, "parallel_mosfets_montecarlo_analysis.jsimba")
        project = ProjectRepository(file_path)
    design = project.GetDesignByName('Design 1 - Cauer')
    param_values = generate_random_values(param)
    design.Circuit.GetDeviceByName('T11').Ron = param_values['Rdson11']
    design.Circuit.GetDeviceByName('T12').Ron = param_values['Rdson12']
    design.Circuit.GetDeviceByName('T11').Rgon = param_values['Rg11']
    design.Circuit.GetDeviceByName('T12').Rgon = param_values['Rg12']
    design.Circuit.GetDeviceByName('T11').Rgoff = param_values['Rg11']
    design.Circuit.GetDeviceByName('T12').Rgoff = param_values['Rg12']
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK": 
        print (job.Summary()[:-1])
    manager_result_dict[sim_number] = [param_values['Rdson11'],
                                    param_values['Rdson12'],
                                    param_values['Rg11'],
                                    param_values['Rg12'],
                                    job.GetSignalByName('T11 - Average Total Losses (W)').DataPoints[-1],
                                    job.GetSignalByName('T12 - Average Total Losses (W)').DataPoints[-1],
                                    job.GetSignalByName('T11 - Junction Temperature (°)').DataPoints[-1],
                                    job.GetSignalByName('T12 - Junction Temperature (°)').DataPoints[-1]]

def run_simulation_star(args):
    """
    Helper function used to call run_simulation with a single argument
    """
    return run_simulation(*args)

#############################
#         MAIN SCRIPT       #
#############################

if __name__ == "__main__": # Called only in main thread. It confirms that the code is under main function

    manager = multiprocessing.Manager()
    lock = manager.Lock()
    manager_result_dict = manager.dict()
    pool_args = [[iter, manager_result_dict, lock] for iter in iterations]
    pool = multiprocessing.Pool()
    for _ in tqdm(pool.imap(run_simulation_star, pool_args), total=len(pool_args)):
        pass
    
    # Store results in dedicated dictionnary
    res = {'Rdson11':[], 'Rdson12':[], 'Rg11':[], 'Rg12':[], 'Losses11':[], 'Losses12':[], 'Tj11':[], 'Tj12':[]}
    for item in manager_result_dict.items():
        for key, var_position in zip(res.keys(), range(len(res))):
            res[key].append(item[1][var_position])
    
    # Store results in dataframe to write it in a file
    df = pd.DataFrame(res)
    script_folder = os.path.realpath(os.path.dirname(__file__))
    filename = "montecarlo_parallel_mosfets_" + datetime.now().strftime("%Y-%m-%d")
    df.to_pickle(os.path.join(script_folder, filename + ".pkl"))