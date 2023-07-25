"""
These scripts calculate the efficiency map of the PMSM inverter modeled in "inverter_map.jsimba". The efficiency is calculated for each current and speed references defined in the [0, max_speed_ref; 0 max_current_ref] space. 
Id and Iq references are calculated for each point with MTPA and flux weakening algorithm.

Make sure to run 'pip install -r requirements.txt' to ensure you have the required packages.

##### Requires aesim.simba version 2022.12.13 or higher #####
"""

import numpy,multiprocessing, os
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import numpy as np
import math
from tqdm import tqdm
from aesim.simba import Design, ProjectRepository, License
from datetime import datetime
from scipy.spatial import ConvexHull

#############################
#   SIMULATION PARAMETERS   #
#############################
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense() # Number of PSL Solver 
case_temperature = 80           # Case temperature [Celsius]
Rg = 2.5                        # Gate resistance [Ohm]
switching_frequency = 50000;     # Switching Frequency [Hz]
bus_voltage = 600.0;            # Bus Voltage [V]
max_speed_ref = 4000            # RPM
max_current_ref = 17.0          # A

number_of_speed_points = 10    # Total number of simulations is number_of_speed_points * number_of_current_points
number_of_current_points = 10   # Total number of simulations is number_of_speed_points * number_of_current_points
relative_minimum_speed = 0.2    # fraction of max_speed_ref
relative_minimum_current = 0.2  # fraction of max_torque_ref
simulation_time = 1             # time simulated in each run

NPP = 5.0;                      # PMSM Number of pole pair
PM_Wb = 0.0802;                 # PMSM Ke/NPP
Ld_H = 14.0e-3;                 # Motor Ld [H]
Lq_H = 14.0e-3;                 # Motor Ld [H]
Rs = 0.814                      # Motor Stator Resistance [Ohm]

if os.environ.get("SIMBA_SCRIPT_TEST"): # Accelerate simulation in test environment.
    number_of_speed_points = 2 
    number_of_current_points = 2

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

    log = True # if true, log simulation results

    # Read the jsimba file
    with lock:
        script_folder = os.path.realpath(os.path.dirname(__file__))
        project = ProjectRepository(os.path.join(script_folder , "inverter_map.jsimba"))
    
    simba_full_design = project.GetDesignByName('1-Full Design')

    # Set Test Target Data
    # operating point
    simba_full_design.Circuit.SetVariableValue("speed_rads", str(speed_ref * 2.0 * math.pi/60.0))
    simba_full_design.Circuit.SetVariableValue("idref", str(id_ref))
    simba_full_design.Circuit.SetVariableValue("iqref", str(iq_ref))
    simba_full_design.Circuit.SetVariableValue("Tcase", str(case_temperature))
    
    # inverter settings
    simba_full_design.Circuit.SetVariableValue("fsw", str(switching_frequency))
    simba_full_design.Circuit.SetVariableValue("Vbus", str(bus_voltage))

    # motor settings
    simba_full_design.Circuit.SetVariableValue("PM_Wb", str(PM_Wb))
    simba_full_design.Circuit.SetVariableValue("Npp", str(NPP))
    simba_full_design.Circuit.GetDeviceByName("PMSM1").Rs = str(Rs)
    simba_full_design.Circuit.GetDeviceByName("PMSM1").Ld = str(Ld_H)
    simba_full_design.Circuit.GetDeviceByName("PMSM1").Lq = str(Lq_H)
    simba_full_design.Circuit.GetDeviceByName("Q-axis controller").Definition.GetDeviceByName("Ld").Value = Ld_H
    simba_full_design.Circuit.GetDeviceByName("D-axis controller").Definition.GetDeviceByName("Lq").Value = Lq_H

    # mosfet gate resistances Rgon and Rgoff
    for i in range(1, 6):
        simba_full_design.Circuit.GetDeviceByName("T{0}".format(i)).CustomVariables[0].Value = str(Rg)
        simba_full_design.Circuit.GetDeviceByName("T{0}".format(i)).CustomVariables[1].Value = str(Rg)
        
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
    total_inverter_losses = job.GetSignalByName('Total_losses - Heat Flow').DataPoints[-1]
    actual_torque = job.GetSignalByName('PMSM1 - Te').DataPoints[-1]
    actual_speed_rpm = job.GetSignalByName('speed_rpm - Out').DataPoints[-1]
    input_power = job.GetSignalByName('Input Power:average - Out').DataPoints[-1]
    if (actual_speed_rpm < 0): return; # ERROR 

    if log: print ('{0}> Total Inverter Losses = {1:.2f}W'.format(sim_number, total_inverter_losses))
    if log: print ('{0}> Input Power = {1:.2f}W'.format(sim_number, input_power))
    if log: print ('{0}> Actual Torque = {1:.2f}N.m Id Ref = {2:.2f} A Iq Ref = {3:.2f} A'.format(sim_number, actual_torque, id_ref, iq_ref))
    if log: print ('{0}> Actual Speed = {1:.2f}RPM Speed Ref = {2:.2f} RPM'.format(sim_number, actual_speed_rpm, speed_ref))

    efficiency = 1 - total_inverter_losses / (total_inverter_losses + input_power)
    if log: print ('{0}> Efficiency = {1:.2f}%  Input Power {2:.2f}W total_inverter_losses  {3:.2f}W'.format(sim_number, 100*efficiency, input_power, total_inverter_losses))
    result_dict[sim_number] = [total_inverter_losses, actual_torque, actual_speed_rpm, efficiency]

def run_simulation_star(args):
    """
    Helper function used to call run_simulation with a single argument
    """
    return run_simulation(*args)

def show_heatmap(x, y, z):
    """
    Show the efficiency points and add a contour plot for efficiency values
    """
    # Create grid values first.
    xi, yi = np.linspace(x.min(), x.max(), 100), np.linspace(y.min(), y.max(), 100)

    # Linearly interpolate the data (x, y) on a grid defined by (xi, yi).
    triang = tri.Triangulation(x, y)
    interpolator = tri.LinearTriInterpolator(triang, z)
    Xi, Yi = np.meshgrid(xi, yi)
    zi = interpolator(Xi, Yi)
    fig, (ax1) = plt.subplots(nrows=1)
    
    # Creating outer plot
    points = np.column_stack((x, y))
    hull = ConvexHull(points)
    ax1.plot(points[hull.vertices,0], points[hull.vertices,1], 'k--', lw=2)

    cntr1 = ax1.contourf(xi, yi, zi, levels=100, cmap="PiYG")

    fig.colorbar(cntr1, ax=ax1)
    ax1.plot(x, y, 'ko', ms=1)
    ax1.set(xlim=(0, x.max()), ylim=(0, y.max()))
    ax1.set_xlabel("Speed [RPM]")
    ax1.set_ylabel("Torque [N.m]")
    ax1.set_title("Inverter Losses [W]\nRg={0:.2f}Ω, Fsw={1:.2f}Hz, Vbus={2:.2f}V, T_case={3:.2f}°C".format(Rg,switching_frequency,bus_voltage,case_temperature))
    path= "efficiency_map_"+datetime.now().strftime("%m%d%Y%H%M%S")+".png"
    fig.savefig(path)
    plt.show()

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

    Vo_V = Vdc_V/2.0
    speed_radpsec = speed_rpm/60*2*math.pi
    		
    Beta_MTPA_rad = 0.0
    if abs(Ld_H - Lq_H) > 1.0e-8:
        nume = (-1.0*PM_Wb + math.sqrt(PM_Wb*PM_Wb)+8*(Lq_H-Ld_H)*Ia_A*Ia_A)
        deno = 4.0*(Lq_H - Ld_H)*Ia_A
        Beta_MTPA_rad = math.asin(nume/deno) 
    
    id_MTPA_A = -1.0* Ia_A * math.sin(Beta_MTPA_rad) 
    iq_MTPA_A = Ia_A * math.cos(Beta_MTPA_rad)
    
    Flux_Wb = math.sqrt( math.pow(PM_Wb+Ld_H*id_MTPA_A,2) + math.pow(Lq_H*iq_MTPA_A,2))
    corner_speed_radpsec_mech = ( Vo_V/Flux_Wb) / NPP 
    speed_radpsec_elec = speed_radpsec*NPP
        
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
            if (math.pow(Vo_V/speed_radpsec_elec, 2) -math.pow(Lq_H*iq_FW_A,2) ) < 0.0:
                continue
            
            id_FW_A = (-1.0*PM_Wb + math.sqrt( math.pow(Vo_V/speed_radpsec_elec, 2) -math.pow(Lq_H*iq_FW_A,2) ) )/Ld_H
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
    t = []
    s = []
    e = []
    for i in result_dict.items():
        t.append(i[1][1])
        s.append(i[1][2])
        e.append(i[1][3])
    t= numpy.array(t)
    s= numpy.array(s)
    e= numpy.array(e)
    show_heatmap(s, t, e)