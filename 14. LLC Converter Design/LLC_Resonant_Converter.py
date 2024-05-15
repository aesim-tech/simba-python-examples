"""
LLC Resonant Converter Simulation Script

This is the script explained in the Webinar entitled "Design of a DC-DC Full Bridge LLC resonant converter using SIMBA Python API" https://youtu.be/8LDfKg6U2Lo

This script simulates an LLC Resonant Converter using the aesim.simba package. It analyzes the converter's performance
under various configurations by sweeping parameters such as inductor ratios, quality factors, and frequency ranges.
The results are visualized using matplotlib.

Before running the script, make sure to install the required packages by executing 'pip install -r requirements.txt'.
"""

import numpy as np
import os,multiprocessing, tqdm, math
import matplotlib.pyplot as plt
from aesim.simba import ProjectRepository, License

#############################
#   SIMULATION PARAMETERS   #
#############################
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense() # Number of available parallel simulation license
VIN = 400
VIN_RATED = 400
VIN_MIN = 390
VIN_MAX = 410
VO = 420
VO_RATED = 420
VO_MIN = 300
VO_MAX = 420
PO_RATED = 3300
IO_RATED = PO_RATED / VO_RATED

# Operating conditions
K_LOAD = 1 
F_RES = 200000
N = (VO_MAX+VO_MIN)/(2*VIN_RATED)
N2 = N*N
Ro_RATED = VO_RATED*VO_RATED/PO_RATED
RO_RATED_PRI = Ro_RATED/N2
RO = Ro_RATED/K_LOAD
G_DC_MIN = VO_MIN/(N*VIN_MAX)
G_DC_MAX = VO_MAX/(N*VIN_MIN)

# Sweep parameter
LN_RANGE = [1, 2, 3, 5, 6, 7, 9, 10]
#LN_RANGE = [1, 5, 7, 10]
Q_RANGE = [0.1, 0.13, 0.17, 0.2, 0.25, 0.3, 0.35, 0.4, 0.7, 1]
FIN_RANGE= np.logspace(-1, 0.5, num=100)

if os.environ.get("SIMBA_SCRIPT_TEST"): # Accelerate simulation in test environment.
    LN_RANGE = [7]
    Q_RANGE = [0.4]
    FIN_RANGE= np.logspace(-1, 0.5, num=4)

#############################
#           METHODS         #
#############################

def steadystate_signal(horizon_time, time, *signals):
    """
    Calculate and return the steady-state portion of the given signals based on the specified horizon time.
    
    Args:
    horizon_time (float): The time window to consider for the steady-state portion of the signals.
    time (numpy.ndarray): 1D array of time values corresponding to the signals.
    *signals (numpy.ndarray): One or more 1D arrays containing the signal values.

    Returns:
    tuple: A tuple containing the following elements:
        - steadystate_time (numpy.ndarray): 1D array of time values in the steady-state portion.
        - steadystate_signal_list (list): A list of 1D arrays representing the steady-state portion of each input signal.
    """
    steadystate_maskarray = np.ma.where(time > time[-1] - horizon_time)
    steadystate_time = time[steadystate_maskarray]
    steadystate_signal_list = [signal[steadystate_maskarray] for signal in signals]
    return steadystate_time, *steadystate_signal_list

def run_simulation(Lr, Cr, Lm, fin, sim_number, result_dict, lock):
    """
    Run LLC Open Loop Simulation for the given parameters and place the results in "result_dict"
    """

    log = False # if true, log simulation results
    if log: print ("\n{0}> Running LLC Open loop... (Lr={1:.2f} Cr={2:.2f} Lm={3:.2f})".format(sim_number, Lr, Cr, Lm))

    # Read the jsimba file
    script_folder = os.path.realpath(os.path.dirname(__file__)) 
    file_path = os.path.join(script_folder  , "LLC_Resonant_Converter.jsimba")
    with lock:
        project = ProjectRepository(file_path)
        LLC_open_loop = project.GetDesignByName('LLC Resonant Converter-open loop')


    # Get Elements
    simba_vin = LLC_open_loop.Circuit.GetDeviceByName('vin')
    simba_Lr = LLC_open_loop.Circuit.GetDeviceByName('Lr')
    simba_Cr = LLC_open_loop.Circuit.GetDeviceByName('Cr')
    simba_Lm = LLC_open_loop.Circuit.GetDeviceByName('Lm')
    simba_fin = LLC_open_loop.Circuit.GetDeviceByName('fin')
    simba_fres = LLC_open_loop.Circuit.GetDeviceByName('fres')
    simba_Rout = LLC_open_loop.Circuit.GetDeviceByName('Ro')
    simba_transfo = LLC_open_loop.Circuit.GetDeviceByName('Transfo')

    # Apply parameters
    fsw = F_RES*fin
    LLC_open_loop.TransientAnalysis.TimeStep = 1e-8
    LLC_open_loop.TransientAnalysis.StopAtSteadyState = True
    LLC_open_loop.TransientAnalysis.BaseFrequency = fsw
    LLC_open_loop.TransientAnalysis.BaseFrequencyParameterEnabled = True
    simba_vin.Voltage = VIN_RATED
    simba_Rout.Value = RO
    simba_fres.value = F_RES
    simba_transfo.Ratio = N
    simba_Lr.Value = Lr
    simba_Cr.Value = Cr 
    simba_Lm.Value = Lm
    simba_fin.Value = fin

    # run simulation 
    job = LLC_open_loop.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK": 
        print ("\nSimulation {0} Failed > (Lr={1:.2f} Cr={2:.2f} Lm={3:.2f})".format(sim_number, Lr, Cr, Lm))
        print (job.Summary()[:-1])
        result_dict[sim_number] = [fin, math.nan]
        return; # ERROR 

    if log: print (job.Summary()[:-1])

    #extract steady state results
    horizon_time = 3 / fsw
    time, vout_res = steadystate_signal(
        horizon_time,
        np.array(job.TimePoints),
        np.array(job.GetSignalByName('Ro - Instantaneous Voltage').DataPoints)
        )
    
    # calculate the average of the steady state output voltage using the trapezoidal rule
    t1 = time[0]
    t2 = time[-1]
    vout_sum = 0
    range_idx = range(0, len(time)-1, 1)
    for idx in range_idx:
        vout_sum += (time[idx+1] - time[idx]) * (vout_res[idx+1] + vout_res[idx]) / 2
    vout_average = 1 / (t2 - t1) * vout_sum * 1 / VIN_RATED
    if log: print ("\n{0}> vout_average={1:.3f}".format(sim_number, vout_average))

    result_dict[sim_number] = [fin, vout_average]


def run_simulation_star(args):
    """
    Helper function used to call run_simulation with a single argument
    """
    return run_simulation(*args)

#############################
#         MAIN SCRIPT       #
#############################

# Distribute and run the calculations. Results are saved in result_dict
if __name__ == "__main__": # Called only in main thread.

    manager = multiprocessing.Manager()
    result_dict = manager.dict()
    i=0
    jobs=[]
    lock = manager.Lock()
    pool_args = []
    figure, axs = plt.subplots(nrows=2, ncols=4, figsize=(15, 12))

    # Prepare arguments
    for L, ax in zip(LN_RANGE, axs.ravel()):
        for Q in Q_RANGE:
            Lr = (Q*RO_RATED_PRI)/(2*np.pi*F_RES)
            Cr = 1/(2*np.pi*F_RES*Q*RO_RATED_PRI)
            Lm = L*Lr
            for fin in FIN_RANGE:
                pool_args.append((Lr, Cr, Lm, fin,  i, result_dict, lock));
                i=i+1

    # Run Actual Simulation
    pool = multiprocessing.Pool(number_of_parallel_simulations)
    for _ in tqdm.tqdm(pool.imap(run_simulation_star, pool_args), total=len(pool_args)):
        pass
        
    # Plot curves
    if os.environ.get("SIMBA_SCRIPT_TEST"):
        exit()

    freq_L = []
    Q_L = []
    V_max = []
    i = 0;
    for L, ax in zip(LN_RANGE, axs.ravel()):
        vout_total = []
        vout_total_max = []
        freq = []
        for Q in Q_RANGE:
            vouts = []
            for fin in FIN_RANGE:
                vout_average = result_dict[i][1]
                vouts.append(vout_average)
                i = i+1;
            vout_total.append(vouts)
            vout_total_max.append(max(vouts))
            freq.append(FIN_RANGE)
        for f, V in zip(freq, vout_total):
            ax.plot(f, V)
            ax.plot(f, np.ones_like(f) * G_DC_MAX, linestyle='dashed', linewidth=0.5)
            ax.plot(f, np.ones_like(f) * G_DC_MIN, linestyle='dashed', linewidth=0.5)
            ax.set_xlabel('fn')
            ax.set_ylabel('Peak Gain')
            ax.legend(["Q=" + str(q) for q in Q_RANGE])
            ax.set_title('Ln=' + str(L), loc='left')
        V_max.append(vout_total_max)
        Q_L.append(Q_RANGE)
    for Qe, Vm, Ln in zip(Q_L, V_max, LN_RANGE):
        fig1 = plt.figure("Figure 2")
        plt.plot(Qe, Vm)
        plt.xlabel('Qe')
        plt.ylabel('Max_Gain')
        plt.legend(["Ln=" + str(ln) for ln in LN_RANGE])
    figure.tight_layout
    plt.show()

