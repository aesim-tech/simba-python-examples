import os, multiprocessing
from tqdm import tqdm
from aesim.simba import ProjectRepository, License
import pandas as pd
from datetime import datetime

#############################
#         PARAMETERS        #
#############################
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense() # Number of available Parallel Simulation License

# Define topologies, switches and result dataframes

topos = ['3L-NPC', '3L-T-type', '3L-FC']
switches = dict()
switches['3L-NPC'] = ['T1', 'T2', 'D1', 'D2', 'D5']
switches['3L-T-type'] = ['T1', 'T2', 'T3', 'D1', 'D2', 'D3']
switches['3L-FC'] = ['T1', 'T2', 'D1', 'D2']
all_switches = list(set(switches['3L-NPC'] + switches['3L-T-type'] + switches['3L-FC']))

if os.environ.get("SIMBA_SCRIPT_TEST"): # To accelerate unit tests
    topos = ['3L-NPC']
    end_time = 0.08
else:
    end_time = 1.2

#############################
#           METHODS         #
#############################

def run_simulation(topo, sim_number, manager_result_dict, lock):
    """
    Run SIMBA Simulation and place the results in "manager_result_dict"
    """ 
    log = False # if true, log simulation results

    # Get simba project
    with lock:
        script_folder = os.path.realpath(os.path.dirname(__file__))
        file_path = os.path.join(script_folder, "benchmark_3L_3ph_inverters.jsimba")
        project = ProjectRepository(file_path)

    # Load design and run simulation
    design = project.GetDesignByName(topo)
    design.Circuit.SetVariableValue('ma', str(0.8))
    design.TransientAnalysis.EndTime = end_time
    design.TransientAnalysis.TimeStep = 5e-8
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK" or log: 
        print (job.Summary())

    # Get and store waveforms, losses and Tj
    waveforms = {}
    conduction_loss = {}
    switching_loss = {}
    Tj = {}
    waveforms['U12-data'] = job.GetSignalByName('U12 - Voltage').DataPoints
    waveforms['U12-time'] = job.GetSignalByName('U12 - Voltage').TimePoints
    for s in switches[topo]:
        conduction_loss[s] = job.GetSignalByName(s + ' - Average Conduction Losses (W)').DataPoints[-1]
        switching_loss[s] = job.GetSignalByName(s + ' - Average Switching Losses (W)').DataPoints[-1]
        Tj[s] = max(job.GetSignalByName(s + ' - Junction Temperature (°)').DataPoints)
    
    manager_result_dict[sim_number] = [topo, waveforms, conduction_loss, switching_loss, Tj]

def run_simulation_star(args):
    """
    Helper function used to call run_simulation with a single argument
    """
    return run_simulation(*args)

#############################
#         MAIN SCRIPT       #
#############################

# Distribute and run the calculations. Results are saved in result_dict
if __name__ == "__main__": # Called only in main thread. It confirms that the code is under main function

    manager = multiprocessing.Manager()
    lock = manager.Lock()
    manager_result_dict = manager.dict()

    # Create all scenarii
    pool_args = []
    sim_nb = 0
    # for op_index in range(len(op_points)):
    for topo in topos:
        pool_args.append((topo, sim_nb, manager_result_dict, lock))
        sim_nb += 1
    
    # Start process pool
    pool = multiprocessing.Pool(number_of_parallel_simulations)
    for _ in tqdm(pool.imap(run_simulation_star, pool_args), total=len(pool_args)):
        pass

# Store results in dedicated dictionnary
    res = {}
    res['topo'] = []
    res['waveforms'] = []
    res['conduction'] = []
    res['switching'] = []
    res['Tj'] = []

    for item in manager_result_dict.items():
        for key, var_position in zip(res.keys(), range(len(res))):
            res[key].append(item[1][var_position])

    # Store results in dataframe to write it in a file
    df = pd.DataFrame(res)
    script_folder = os.path.realpath(os.path.dirname(__file__))
    filename = "benchmark_3L_" + datetime.now().strftime("%Y-%m-%d")
    df.to_pickle(os.path.join(script_folder, filename + ".pkl"))
    
