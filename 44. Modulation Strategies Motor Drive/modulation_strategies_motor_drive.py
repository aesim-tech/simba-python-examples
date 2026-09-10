import json
import os, multiprocessing
from tqdm import tqdm
from aesim.simba import ProjectRepository, License
import numpy as np
import pandas as pd
from datetime import datetime


#############################
#         PARAMETERS        #
#############################
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense() # Number of available Parallel Simulation License

Npp = 4 # Number of pole pairs of the motor

# Define two operating points
rpm_speed_refs = {'B': 2000, 'D': 4000}
torque_refs = {'B': 250, 'D': 20}
id_refs = {'B': -157.47, 'D': -19.32}
iq_refs = {'B': 157.03, 'D': 11.52}


refs = {
    "rpm_speed_refs": rpm_speed_refs,
    "torque_refs": torque_refs,
    "id_refs": id_refs,
    "iq_refs": iq_refs,
}
script_folder = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(script_folder, "operating_points.json"), "w") as f:
    json.dump(refs, f, indent=4)


# Define modulation strategies and switching frequencies
modulations = ['SVPWM', 'DPWM', 'SPWM']
switching_frequencies = [2e4, 4e4, 6e4]

if os.environ.get("SIMBA_SCRIPT_TEST"): # To accelerate unit tests
    modulations = ['SVPWM']
    switching_frequencies = [2e4]

#############################
#           METHODS         #
#############################

def run_simulation(op_point_key, fpwm, modulation_key, sim_number, manager_result_dict, lock):
    """
    Run SIMBA Simulation and place the results in "manager_result_dict"
    """ 
    log = False # if true, log simulation results

    # Get simba project
    with lock:
        script_folder = os.path.realpath(os.path.dirname(__file__))
        file_path = os.path.join(script_folder, "modulation_strategies_motor_drive.jsimba")
        project = ProjectRepository(file_path)
    
    # Get design according modulation strategy
    design = project.GetDesignByName(modulation_key+'_modulation')

    # Set JMAG motor model reference
    motor = design.Circuit.GetDeviceByName('JmagRTMotor')
    motor.RttFilePath.UserValue = os.path.join(script_folder, 'withHF_4000rpm20Nm.rtt')
    
    # Set speeds and id, iq references
    speed_source_rads = design.Circuit.GetDeviceByName('W1')
    speed_source_rads.Voltage = float(rpm_speed_refs[op_point_key]*np.pi/30)
    id_ref_block = design.Circuit.GetDeviceByName('Id_ref')
    id_ref_block.Value = id_refs[op_point_key]
    iq_ref_block = design.Circuit.GetDeviceByName('Iq_ref')
    iq_ref_block.Value = iq_refs[op_point_key]
    carrier = design.Circuit.GetDeviceByName('Carrier')
    carrier.Frequency = fpwm

    # Run calculation
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK" or log: 
        print (job.Summary())
        return

    # Get inverter Losses
    conduction_losses = sum([job.GetSignalByName('T' + str(n) + ' - Average Conduction Losses (W)').DataPoints[-1] for n in range(1, 7)])
    switching_losses = sum([job.GetSignalByName('T' + str(n) + ' - Average Switching Losses (W)').DataPoints[-1] for n in range(1, 7)])
                                
    # Get motor losses
    copper_losses = job.GetSignalByName('JmagRTMotor - Copper Loss (average)').DataPoints[-1] 
    iron_losses = job.GetSignalByName('JmagRTMotor - Iron Loss (average)').DataPoints[-1] 
    if log:
        # Get Torque
        end_time = job.GetSignalByName('JmagRTMotor - Te').TimePoints[-1]
        mask_time = job.GetSignalByName('JmagRTMotor - Te').TimePoints > (end_time - 60 / rpm_speed_refs[op_point_key] / Npp)
        torque = job.GetSignalByName('JmagRTMotor - Te').DataPoints[mask_time]
        average_torque = round(np.mean(torque) / 10) * 10
        print(f"Check speed = {rpm_speed_refs[op_point_key]} rpm - Torque = {average_torque} Nm for {modulation_key} - {round(fpwm/1000)} kHz", conduction_losses, switching_losses, copper_losses, iron_losses)

    manager_result_dict[sim_number] = [op_point_key, modulation_key, fpwm, conduction_losses, switching_losses, copper_losses, iron_losses]

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
    for op_point_key in rpm_speed_refs.keys():
        id_ref = id_refs[op_point_key]
        iq_ref = iq_refs[op_point_key]
        for mod_key in modulations:
            for fpwm in switching_frequencies:
                pool_args.append((op_point_key, fpwm, mod_key, sim_nb, manager_result_dict, lock))
                sim_nb += 1
    
    # Start process pool
    pool = multiprocessing.Pool(number_of_parallel_simulations)
    for _ in tqdm(pool.imap(run_simulation_star, pool_args), total=len(pool_args)):
        pass

    # Store results in dedicated dictionnary
    res = dict()
    res['op_point'] = []
    res['modulation'] = []
    res['fpwm'] = []
    res['conduction'] = []
    res['switching'] = []
    res['copper'] = []
    res['iron'] = []

    for item in manager_result_dict.items():
        for key, var_position in zip(res.keys(), range(len(res))):
            res[key].append(item[1][var_position])

    # Store results in dataframe to write it in a file
    df = pd.DataFrame(res)
    filename = "mod_strat_motor_drive_" + datetime.now().strftime("%Y-%m-%d")
    df.to_pickle(os.path.join(script_folder, filename + ".pkl"))

    