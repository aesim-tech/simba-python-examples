#%% Load modules
from aesim.simba import JsonProjectRepository
from datetime import datetime
import matplotlib.pyplot as plt
import os
import numpy as np
import copy

#%%  Methods
def run_single_analysis(design, param, analysis_name, overshoot):
    """
    run Simba simulation of the circuit and store overshoot result in a dictionnary with the analysis name as the key.

    :param: Simba circuit
    :param: dictionnary of circuit parameters
    :param: analysis name (string)
    :overshoot: dictionnary to store overshoot results
    """
    
    log = False
    for key in param.keys():
        design.Circuit.GetDeviceByName(key).Value = param[key]
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    t = job.TimePoints
    vout = job.GetSignalByName('R2 - Voltage').DataPoints
    vout_max = max(vout)
    vout_final = vout[-1]
    
    # Perform overshoot calculation and store results
    overshoot[analysis_name] = vout_max - vout_final
    
    if log: # Print intermediate results
        print("\n{0}Run analysis: " + analysis_name +
              "\n(vout)max = {0:.4f} V (vout)average = {0:.4f} V Overshoot = {0:.4f}".format(vout_max, vout_final, overshoot[analysis_name]))

def compute_sensitivity(nominal_param, rel_perturbation, overshoot, sensitivity):
    """
    compute sensitivity for each circuit parameter

    :param: nominal circuit parameters
    :param: relative perturbation
    :overshoot: dictionnary of overshoot results
    :sensitivity: dictionnary of sensitivity results
    """
    for key in nominal_param.keys():
        sensitivity[key] = abs((overshoot[key] - overshoot['nominal']) / (nominal_param[key] * rel_perturbation)) * (nominal_param[key] / overshoot['nominal'])

def write_report(sensitivity):
    report_list = ['\n################################\n' +
                   '# Sensitivity Analysis Report \n' +
                   '# Date: ' + datetime.now().strftime("%m-%d-%Y \n# Hour: %H:%M:%S") + "\n" +
                   '################################\n\n' ]
    for key in sensitivity.keys():
        report_list.append('Sensitivity of ' + key + ' is {0:.4f}'.format(sensitivity[key]) + "\n")
    report_list.append('\nThe most sensitive parameter for overshoot measurement is the parameter which has the highest sensitivity value')
    report_to_print = ''.join(str(e) for e in report_list)
    print(report_to_print)
    file = open(script_folder + '/report' + datetime.now().strftime("%m%d%Y%H%M") + '.txt', 'w')
    file.write(report_to_print)
    file.close()

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
file_path = os.path.join(script_folder, "sensitivity_analysis.jsimba")
project = JsonProjectRepository(file_path)
RLC = project.GetDesignByName('RLC')

#%% Run simulations
nominal_param = {'R1':100, 'C1':1e-6, 'L1':2.5e-2, 'R2':1e3}
overshoot = dict()
run_single_analysis(RLC, nominal_param, 'nominal', overshoot)

rel_perturbation = 0.1
for key in nominal_param.keys():
    perturb_param = copy.deepcopy(nominal_param)
    perturb_param[key] = nominal_param[key] * (1 + rel_perturbation)
    run_single_analysis(RLC, perturb_param, key, overshoot)

#%% Sensitivity computation
sensitivity = dict()
compute_sensitivity(nominal_param, rel_perturbation, overshoot, sensitivity)

#%% Print report
write_report(sensitivity)

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
