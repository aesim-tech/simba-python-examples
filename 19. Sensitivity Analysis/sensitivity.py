#%% Load modules
from aesim.simba import JsonProjectRepository
from datetime import datetime
import matplotlib.pyplot as plt
import os
import numpy as np
import copy

#%% Load functions

def steadystate_signal(horizon_time, time, *signals):
    """steadystate_signal() returns time ndarray and a list of signals on the horizon_time"""

    steadystate_maskarray = np.ma.where(time > time[-1] - horizon_time)
    steadystate_time = time[steadystate_maskarray]
    steadystate_signal_list = [signal[steadystate_maskarray] for signal in signals]
    return steadystate_time, *steadystate_signal_list

def average_value(time, waveform):
    """average_value() returns the average value of a time waveform equal time steps are not required"""

    cum_sum = 0
    range_idx = range(0, len(time)-1, 1)

    for idx in range_idx:
        cum_sum += (time[idx + 1] - time[idx]) * (waveform[idx+1] + waveform[idx]) /2
    return (1 / (time[-1] - time[0]) * cum_sum)

def run_single_analysis(design, param, analysis_name, overshoot):
    """
    run Simba simulation of the circuit and store sensitivity result in a dictionnary whose key is the analysis name

    :param: Simba circuit
    :param: dictionnary of circuit parameters
    :param: analysis name (string)
    :sensitivity: dictionnary to store sensitivity results
    """
    
    log = True
    for key in param.keys():
        design.Circuit.GetDeviceByName(key).Value = param[key]
    #design.Circuit.GetDeviceByName(analysis_name).Value = param[analysis_name] * (1 + rel_perturbation)
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    t = job.TimePoints
    Vout = job.GetSignalByName('R2 - Voltage').DataPoints
    vout_max = max(Vout)

    # steady state between 0.0050 and 0.0060
    horizon_time = 0.001  
    t, Vout = steadystate_signal(horizon_time,
                                 np.array(job.TimePoints),
                                 np.array(job.GetSignalByName('R2 - Voltage').DataPoints))

    # Perform average calculation between 0.0050 and 0.0060
    Vout = np.array(Vout)
    Vout_average = average_value(t, Vout)
    
    # Perform overshoot calculation and store results
    overshoot[analysis_name] = vout_max - Vout_average

    # Print results
    if log:
        print("\n{0}Run analysis: " + analysis_name +
              "\n(Vout)max = {0:.4f} V (Vout)average = {0:.4f} V Overshoot = {0:.4f}".format(vout_max, Vout_average, overshoot[analysis_name]))

def plot_bar(Tab1 = [], 
        Tab2 = [], 
        largeur_barre = 0.3,
        Etiquette = [],
        FigAxe = "ax1",
        show = False,
        plot = plt, Tab1_abscisse = [], 
        dxticks = 0, mxticks = 2, 
        xlim = [], ylim = [],
        color_tab1 = 'orange',
        Legend = ['SIMBA', 'test'],
        ylabel='Average or rms values'):


        if Tab1_abscisse == []:
                Tab1_abscisse = range(len(Tab1)) # Position des barres de la categorie 1
        
        if Tab2 != []:
                Tab2_abscisse = [i + largeur_barre for i in Tab1_abscisse] # Position des barres de la cat 2

        plot.bar(Tab1_abscisse, Tab1, width = largeur_barre, color = color_tab1, # Barres cat 1
                edgecolor = 'black', linewidth = 2)
        
        if Tab2 != []:
                plot.bar(Tab2_abscisse, Tab2, width = largeur_barre, color = 'yellow', # Barres cat 2
                        edgecolor = ['black' for i in Tab1], linewidth = 2)

        plot.xticks([dxticks+r + largeur_barre / mxticks for r in range(len(Tab1))], # Etiquettes
                Etiquette)

        FigAxe.set_ylabel(ylabel)

        if ylim !=[]:
                plt.ylim(ylim)
        if xlim !=[]:
                plt.xlim(xlim)

        if Tab2 != []:
            plot.legend(Legend)

        if show == True :
                plot.show()


#%% Get project
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "sensitivity.jsimba")
project = JsonProjectRepository(file_path)
RLC = project.GetDesignByName('RLC')
# Create empty dict to store results
overshoot = dict()
# Set relative perturbation
rel_perturbation = 0.1

#%% Nominal simulation

nominal_param = {'R1':100, 'C1':1e-6, 'L1':2.5e-2, 'R2':1e3}
run_single_analysis(RLC, nominal_param, 'nominal', overshoot)

for key in nominal_param.keys():
    perturb_param = copy.deepcopy(nominal_param)
    perturb_param[key] = nominal_param[key] * (1 + rel_perturbation)
    run_single_analysis(RLC, perturb_param, key, overshoot)


#%% Sensitivity param
report_list = ['\n################################\n' +
                   '# Sensitivity Analysis Report \n' +
                   '# Date: ' + datetime.now().strftime("%m-%d-%Y \n# Hour: %H:%M:%S") + "\n" +
                   '################################\n\n' ]
sensitivity = dict()
for key in nominal_param.keys():
    sensitivity[key] = abs((overshoot[key] - overshoot['nominal']) / (nominal_param[key] * rel_perturbation)) * (nominal_param[key] / overshoot['nominal'])
    report_list.append('Sensitivity of ' + key + ' is {0:.4f}'.format(sensitivity[key]) + "\n")

report_to_print = ''.join(str(e) for e in report_list)


#%% Plot figure with both graphs and Histogram
fig = plt.figure(figsize = (16, 9))

ax = fig.add_subplot(111)
plot_bar(Tab1 = [sensitivity['R2'], sensitivity['R1'], sensitivity['C1'], sensitivity['L1']], 
        largeur_barre = 0.3,
        Etiquette = ['R2', 'R1', 'C1', 'L1',],
        FigAxe = ax, 
        mxticks = 32,
        ylabel = 'Sensitivity rank',
        color_tab1 = 'blue')

fig.tight_layout()
plt.show()

file = open(script_folder + '/report' + datetime.now().strftime("%m%d%Y%H%M") + '.txt', 'w')
file.write(report_to_print)
file.close()