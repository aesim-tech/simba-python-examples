"""
Customization of efficiency map script available in python examples
"""

import numpy, multiprocessing, os
import math
from tqdm import tqdm
from aesim.simba import ProjectRepository


#############################
#   SIMULATION PARAMETERS   #
#############################
number_of_parallel_simulations = 2 # Number of PSL Solver 
case_temperature = 80           # Case temperature [Celsius]
Rg = 4.5                         # Gate resistance [Ohm]
switching_frequency = 50000;     # Switching Frequency [Hz]
bus_voltage = 500.0;            # Bus Voltage [V]
max_speed_ref = 4000            # RPM
max_current_ref = 100.0          # A

number_of_speed_points = 15    # Total number of simulations is number_of_speed_points * number_of_current_points (we can put 2 for faster results but less accurate)
number_of_current_points = 15   # Total number of simulations is number_of_speed_points * number_of_current_points (we can put 2 for faster results but less accurate)
relative_minimum_speed = 0.2    # fraction of max_speed_ref
relative_minimum_current = 0.2  # fraction of max_torque_ref
simulation_time = 0.5             # time simulated in each run

# Get motor parameters from Simba file
current_folder = os.path.dirname(os.path.abspath(__file__))
project = ProjectRepository(os.path.join(current_folder , "wolfspeed_evaluation.jsimba"))
simba_full_design = project.GetDesignByName('Design')
Ld_H = float(simba_full_design.Circuit.GetVariableValue("Ld"))
Lq_H = float(simba_full_design.Circuit.GetVariableValue("Lq"))
PM_Wb = float(simba_full_design.Circuit.GetVariableValue("Phi_mag"))
NPP = float(simba_full_design.Circuit.GetVariableValue("NPP"))

#############################
#           METHODS         #
#############################
def run_simulation(id_ref, iq_ref, speed_ref, case_temperature, Rg, sim_number, result_dict, lock):
    """
    Run SIMBA Simulation of the design "Full Design" and place the results in "result_dict"

    :param: id_ref, d-axis current refereance[A]
    :param: iq_ref, q-axis current refereance[A]    
    :param: speed_ref, Speed Reference [RPM]
    :param: case_temperature, Case Temperature [Celsius]
    :param: Rg, Gate Resistance [Ohm]
    :param: sim_number, Simulation Number. Used for log purpose [N.m]
    :param: result_dict, Thread safedictionnary used to store results [N.m]
    :param: lock, Mutex. Used to avoid race conditions.
    """

    log = False # if true, log simulation results

    # Read the jsimba file
    with lock:
        current_folder = os.path.dirname(os.path.abspath(__file__))
        project = ProjectRepository(os.path.join(current_folder , "wolfspeed_evaluation.jsimba"))
    
    simba_full_design = project.GetDesignByName('Design')

    # Set Test Target Data
    # operating point
    simba_full_design.Circuit.SetVariableValue("RPM", str(speed_ref))
    simba_full_design.Circuit.GetDeviceByName("Id_ref").Value = id_ref
    simba_full_design.Circuit.GetDeviceByName("Iq_ref").Value = iq_ref
    
    # inverter settings
    simba_full_design.Circuit.SetVariableValue("Tcase", str(case_temperature))
    simba_full_design.Circuit.SetVariableValue("fpwm", str(switching_frequency))
    simba_full_design.Circuit.SetVariableValue("DC", str(bus_voltage))

    for i in range(1, 6):
        simba_full_design.Circuit.GetDeviceByName("T{0}".format(i)).Rgon = Rg
        
    if log: print ("\n{0}> Running Full Model... (Id_ref={1:.2f} A Iq_ref={2:.2f} A speed_ref={3:.2f} RPM)".format(sim_number, id_ref, iq_ref, speed_ref))

    # Run Simulation
    simba_full_design.TransientAnalysis.EndTime = simulation_time
    job = simba_full_design.TransientAnalysis.NewJob()
    status = job.Run()
    
    if str(status) != "OK": 
        print (job.Summary()[:-1])
        return; # ERROR 
    if log: print (job.Summary()[:-1])

    # Read and return results
    inverter_losses = job.GetSignalByName('Inverter_Losses - Heat Flow').DataPoints[-1]
    motor_losses = job.GetSignalByName('JmagRTMotor1 - Total Loss (average)').DataPoints[-1]
    actual_torque = job.GetSignalByName('JmagRTMotor1 - Te').DataPoints[-1]
    actual_speed_rpm = job.GetSignalByName('speed_rpm - Out').DataPoints[-1]
    input_power = job.GetSignalByName('Input Power:average - Out').DataPoints[-1]
    
    Pout= job.GetSignalByName('Pout - Out').DataPoints[-1]

    if (actual_speed_rpm < 0): return; # ERROR 

    if log: print ('{0}> Inverter Losses = {1:.2f}W'.format(sim_number, inverter_losses))
    if log: print ('{0}> Motor Losses = {1:.2f}W'.format(sim_number, motor_losses))
    if log: print ('{0}> Input Power = {1:.2f}W'.format(sim_number, input_power))
    if log: print ('{0}> Actual Torque = {1:.2f}N.m Id Ref = {2:.2f} A Iq Ref = {3:.2f} A'.format(sim_number, actual_torque, id_ref, iq_ref))
    if log: print ('{0}> Actual Speed = {1:.2f}RPM Speed Ref = {2:.2f} RPM'.format(sim_number, actual_speed_rpm, speed_ref))

    total_losses = inverter_losses + motor_losses
    efficiency = 1 - total_losses / (total_losses + input_power)
    if log: print ('{0}> Efficiency = {1:.2f}%  Input Power {2:.2f}W total_losses  {3:.2f}W'.format(sim_number, 100*efficiency, input_power, total_losses))
    result_dict[sim_number] = [inverter_losses, motor_losses, actual_torque, actual_speed_rpm, efficiency, input_power, Pout]

def run_simulation_star(args):
    """
    Helper function used to call run_simulation with a single argument
    """
    return run_simulation(*args)

def SelectIdIq(ref_idiq, current_ref, speed_ref):
    """
    Calculate Id and Iq references calculated with MTPA and flux weakening algorithm.
    Source: S. Morimoto, Y. Takeda, T. Hirasa and K. Taniguchi, "Expansion of operating limits for permanent magnet motor by current vector control considering inverter capacity," in IEEE Transactions on Industry Applications, vol. 26, no. 5, pp. 866-871, Sept.-Oct. 1990, doi: 10.1109/28.60058.
    Args:
        ref_idiq ([float, float]): Used to store the Id&Iq references calculated by this function
        current_ref (float): current reference
        speed_ref (float): speed reference

    Returns:
        boolean: True if success, False is this point is not achieveble
    """
    ret = False
    Vdc_V = bus_voltage
    Ia_A = current_ref
    speed_rpm = speed_ref

    Vo_V = Vdc_V / 2.0
    speed_radpsec = speed_rpm / 60 * 2 * math.pi
    		
    Beta_MTPA_rad = 0.0
    if abs(Ld_H - Lq_H) > 1.0e-8:
        #nume = (-1.0 * PM_Wb + math.sqrt(PM_Wb*PM_Wb) + 8 * (Lq_H - Ld_H) * Ia_A * Ia_A)
        nume = -PM_Wb + math.sqrt(PM_Wb**2 + 8 * (Lq_H - Ld_H)**2  * Ia_A**2)
        deno = 4.0 * (Lq_H - Ld_H) * Ia_A
        Beta_MTPA_rad = math.asin(nume / deno) 
    
    id_MTPA_A = -1.0 * Ia_A * math.sin(Beta_MTPA_rad) 
    iq_MTPA_A = Ia_A * math.cos(Beta_MTPA_rad)
    
    Flux_Wb = math.sqrt(math.pow(PM_Wb + Ld_H*id_MTPA_A, 2) + math.pow(Lq_H * iq_MTPA_A, 2))
    corner_speed_radpsec_mech = ( Vo_V / Flux_Wb) / NPP 
    speed_radpsec_elec = speed_radpsec * NPP
        
    if speed_radpsec < corner_speed_radpsec_mech:
    #% MTPA (Mode 1)
        ref_idiq[0] = id_MTPA_A
        ref_idiq[1] = iq_MTPA_A
        ret = True
    else :
    #	% Flux weakening (Mode 2)
        iq_FW_A = iq_MTPA_A
        for i in range(100):
            iq_A_old = iq_FW_A;
            if (math.pow(Vo_V / speed_radpsec_elec, 2) - math.pow(Lq_H*iq_FW_A,2) ) < 0.0:
                continue
            
            id_FW_A = (-1.0*PM_Wb + math.sqrt(math.pow(Vo_V/speed_radpsec_elec, 2) - math.pow(Lq_H*iq_FW_A,2) ) )/Ld_H
            if(Ia_A*Ia_A - id_FW_A*id_FW_A < 0.0):
                continue
            iq_FW_A = math.sqrt(Ia_A*Ia_A - id_FW_A*id_FW_A)
            if math.fabs(iq_FW_A -iq_A_old) < 1.0e-3 :
                ref_idiq[0] = id_FW_A
                ref_idiq[1] = iq_FW_A	
                ret = True
                break
    return ret
            
#############################
#         MAIN SCRIPT       #
#############################

# Distribute and run the calculations. Results are saved in result_dict
if __name__ == "__main__": # Called only in main thread. It confirms that the code is under main function

    #initialization
    min_speed_ref = relative_minimum_speed * max_speed_ref;
    min_current_ref = relative_minimum_current * max_current_ref;
    
    speed_refs = numpy.arange(min_speed_ref, max_speed_ref, (max_speed_ref - min_speed_ref)/number_of_speed_points)
    current_refs = numpy.arange(min_current_ref, max_current_ref, (max_current_ref - min_current_ref)/number_of_current_points)
    
    manager = multiprocessing.Manager()
    result_dict = manager.dict()
    i=0
    jobs=[]
    lock = manager.Lock()
    pool_args = []

    # Create the run_simulation(...) arguments for each scenario
    for current_ref in current_refs:
        for speed_ref in speed_refs:
            
            ref_idiq = [0.0, 0.0]
            ret = SelectIdIq(ref_idiq, current_ref, speed_ref)
            
            if ret == True:
                pool_args.append((ref_idiq[0], ref_idiq[1], speed_ref, case_temperature, Rg,  i, result_dict, lock));
                i=i+1

    # Create and start the processing pool
    pool = multiprocessing.Pool(number_of_parallel_simulations)
    for _ in tqdm(pool.imap(run_simulation_star, pool_args), total=len(pool_args)):
        pass

    # plot the efficency map
    inverter_losses = []
    motor_losses = []
    input_power= []
    Pout=[]
    t = []
    s = []
    e = []
    for i in result_dict.items():
        inverter_losses.append(i[1][0])
        motor_losses.append(i[1][1])
        t.append(i[1][2])
        s.append(i[1][3])
        e.append(i[1][4])
        input_power.append(i[1][5])
        Pout.append(i[1][6])
    inverter_losses = numpy.array(inverter_losses)
    motor_losses = numpy.array(motor_losses)
    input_power = numpy.array(input_power)
    Pout =  numpy.array(Pout)
    t = numpy.array(t)
    s = numpy.array(s)
    e = numpy.array(e)
    current_folder = os.path.dirname(os.path.abspath(__file__))
    numpy.savetxt(os.path.join(current_folder, "results/inverter_losses.txt"), inverter_losses)
    numpy.savetxt(os.path.join(current_folder,"results/motor_losses.txt"), motor_losses)
    numpy.savetxt(os.path.join(current_folder,"results/input_power.txt"), input_power)
    numpy.savetxt(os.path.join(current_folder,"results/torque.txt"), t)
    numpy.savetxt(os.path.join(current_folder,"results/speed.txt"), s)
    numpy.savetxt(os.path.join(current_folder,"results/efficiency.txt"), e)
    numpy.savetxt(os.path.join(current_folder,"results/Pout.txt"), Pout)
