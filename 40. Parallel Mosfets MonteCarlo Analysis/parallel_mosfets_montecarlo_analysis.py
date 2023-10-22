#%% Load modules
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

iterations = range(500)
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
    
    # Plot figures 
    fig = plt.figure(figsize = (16, 9))

    ax1 = fig.add_subplot(241)
    plot1 = ax1.plot(iterations, res['Losses11'], linestyle='', color='green', marker='o', markerfacecolor='blue')
    ax1.set_xlabel('iteration', fontsize = 9)
    ax1.set_ylabel('Losses', fontsize = 9)
    ax1.set_title("Losses T11", fontsize = 9)

    ax2 = fig.add_subplot(242)
    plot1 = ax2.plot(iterations, res['Losses12'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax2.set_xlabel("iteration", fontsize = 9)
    ax2.set_ylabel("Losses", fontsize = 9)
    ax2.set_title("Losses T12", fontsize = 9)

    ax3 = fig.add_subplot(245)
    plot1 = ax3.plot(res['Rdson11'], res['Losses11'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax3.set_xlabel("Rdson", fontsize = 9)
    ax3.set_ylabel("Losses", fontsize = 9)
    ax3.set_title("Losses T11 vs Rdson 11", fontsize = 9)

    ax4 = fig.add_subplot(246)
    plot1 = ax4.plot(res['Rdson12'], res['Losses11'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax4.set_xlabel("Rdson", fontsize = 9)
    ax4.set_ylabel("Losses", fontsize = 9)
    ax4.set_title("Losses T12 vs Rdson 11", fontsize = 9)

    ax5 = fig.add_subplot(247)
    plot1 = ax5.plot(res['Rdson12'], res['Losses11'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax5.set_xlabel("Rdson", fontsize = 9)
    ax5.set_ylabel("Losses", fontsize = 9)
    ax5.set_title("Losses T11 vs Rdson 12", fontsize = 9)

    ax6 = fig.add_subplot(248)
    plot1 = ax6.plot(res['Rdson12'], res['Losses12'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax6.set_xlabel("Rdson", fontsize = 9)
    ax6.set_ylabel("Losses", fontsize = 9)
    ax6.set_title("Losses T12 vs Rdson 12", fontsize = 9)

    fig.tight_layout(pad = 2)
    fig.savefig(os.path.join(script_folder, filename + ".png"))
    plt.show()
    