#%% Load modules
import os
import random
import numpy as np
from aesim.simba import ProjectRepository
import matplotlib.pyplot as plt
import pandas as pd


def generate_random_values(circuit):
    """
    generate random values of circuit parameters given as a dictionnary

    :param: dictionnary of the different circuit elements (inductor, capacitor, resistor...)
    """
    circuit_values = {}
    for component, values in circuit.items():
        nominal_value = values['nominal']
        tolerance = values['tolerance']
        min_value = nominal_value - (tolerance * nominal_value)
        max_value = nominal_value + (tolerance * nominal_value)
        circuit_values[component] = random.uniform(min_value, max_value)
    return circuit_values

#%% Define number of iterations, nominal and tolerance values for all circuit elements
iterations = range(1000)
circuit = {
           'inductor' : {'nominal': 25e-3, 'tolerance': 0.4},
           'resistor' : {'nominal': 100, 'tolerance': 0.3}
          }

#%% Load project and igbt device
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "montecarlo_worstcase_analysis.jsimba")
project = ProjectRepository(file_path)
design = project.GetDesignByName('Design 1')
L1_values = []
R2_values = []
peak_voltages = []
peak_currents = []

for iter in iterations:
    circuit_values = generate_random_values(circuit)
    design.Circuit.GetDeviceByName('L1').Value = circuit_values['inductor']
    design.Circuit.GetDeviceByName('R2').Value = circuit_values['resistor']
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    L1_values.append(circuit_values['inductor'])
    R2_values.append(circuit_values['resistor'])
    peak_voltages.append(max(np.array(job.GetSignalByName('R1 - Voltage').DataPoints))) 
    peak_currents.append(max(np.array(job.GetSignalByName('L1 - Current').DataPoints)))

#%% Create a dataframe to store results
results = pd.DataFrame({"peak_voltages":peak_voltages, "peak_currents":peak_currents, "L1":L1_values, "R2":R2_values})
results

#%% Plot figures 
fig = plt.figure(figsize = (16, 9))

ax1 = fig.add_subplot(241)
plot1 = ax1.plot(iterations, peak_voltages, linestyle='', color='green', marker='o', markerfacecolor='blue')
ax1.set_xlabel('iteration', fontsize = 9)
ax1.set_ylabel('Vout_peak', fontsize = 9)
ax1.set_title("Output Voltage", fontsize = 9)

ax2 = fig.add_subplot(242)
plot1 = ax2.plot(iterations, peak_currents, linestyle='', color='red', marker='o', markerfacecolor='purple')
ax2.set_xlabel("iteration", fontsize = 9)
ax2.set_ylabel("IL1_peak", fontsize = 9)
ax2.set_title("Inductor Current", fontsize = 9)

ax3 = fig.add_subplot(245)
plot1 = ax3.plot(R2_values, peak_currents, linestyle='', color='red', marker='o', markerfacecolor='purple')
ax3.set_xlabel("R2_values", fontsize = 9)
ax3.set_ylabel("IL1_peak", fontsize = 9)
ax3.set_title("Inductor current vs R2 values dependency", fontsize = 9)

ax4 = fig.add_subplot(246)
plot1 = ax4.plot(L1_values, peak_currents, linestyle='', color='red', marker='o', markerfacecolor='purple')
ax4.set_xlabel("L1_values", fontsize = 9)
ax4.set_ylabel("IL1_peak", fontsize = 9)
ax4.set_title("Inductor current vs L1 values dependency", fontsize = 9)

ax5 = fig.add_subplot(247)
plot1 = ax5.plot(R2_values, peak_voltages, linestyle='', color='red', marker='o', markerfacecolor='purple')
ax5.set_xlabel("R2_values", fontsize = 9)
ax5.set_ylabel("Vout_peak", fontsize = 9)
ax5.set_title("Output voltage vs R2 values dependency", fontsize = 9)

ax6 = fig.add_subplot(248)
plot1 = ax6.plot(L1_values, peak_voltages, linestyle='', color='red', marker='o', markerfacecolor='purple')
ax6.set_xlabel("L1_values", fontsize = 9)
ax6.set_ylabel("Vout_peak", fontsize = 9)
ax6.set_title("Output voltage vs L1 values dependency", fontsize = 9)

fig.tight_layout(pad = 2)
plt.show()