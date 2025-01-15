"""
This python script proposes an approach for fuel cell modeling in SIMBA
- A first step proposes an extraction of model parameters from experimental curves
- A second step proposes the implementation of 3 different models (with C-Code, a PWL resistor and 3rd model which includes a dynamic)
"""
# %%
import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from aesim.simba import ProjectRepository

# %%############################################
# 1- Get main parameters of the Fuel Cell Models
###############################################

print('1- Main parameters of Fuel Cell Models')

current_folder = os.path.dirname(os.path.abspath(__file__))
data = pd.read_csv(os.path.join(current_folder  , "fuelcell_vi_curve.csv"))
data_current = data['Current (A)'].to_numpy()
data_stack_voltage = data['Voltage (V)'].to_numpy()
ncells = 440
data_voltage = data_stack_voltage / ncells

# Assume an open-circuit voltage
Eth = 1.1

# Extract parameters from polarization curve
def get_fuelcell_voltage(ifc, A, io, B, rohm, iLim):
    vfc = Eth - A * np.log(ifc / io) + B * np.log(1 - ifc / iLim) - rohm * ifc
    return vfc

[A, io, B, rohm, iLim], _ = curve_fit(get_fuelcell_voltage, data_current, data_voltage, bounds=((1e-9, 1e-9, 1e-9, 1e-6, max(data_current)), (1e-1, 1, 3e-1, 1e-1, 2*max(data_current))))

# Evaluate unknown parameters
jLim = 1.5                  # typical limit current density (1 to 2 A / cm²)
area = iLim / jLim          # estimate area (cm²)
double_layer_cm2 = 5e-3     # typical double layer capacitor (5 mF / cm²)
CdL = 5e-3 * area           # estimate double layer capacitor

# Resume found characteristics
print("A = {0:.4f} V/A".format(A))
print("io = {0:.4f} A".format(io))
print("B = {0:.4f} V/A".format(B))
print("rohm = {0:.2e} Ohms".format(rohm))
print("iLim = {0:.0f} A" .format(iLim))
print("Estimated area = {0:.0f} cm²".format(area))

model_voltage = Eth  - A * np.log(data_current / io) + B * np.log(1 - data_current / iLim) - rohm * data_current

import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot(data_current, data_voltage, color='red', linestyle='', marker='o', markersize=4, label='data')
ax.plot(data_current, model_voltage, color='darkblue', label='model')
ax.set_ylabel('Voltage (V)')
ax.set_xlabel('Current (A)')
ax.set_title('Data & Model Fuel Cell Voltages')
ax.legend()
ax.grid()
plt.show()


# %%###########################################################
# 2- Get PWL resistor to model activation and diffusion losses
###############################################################

print('2- Get PWL resistor to model activation and diffusion losses in 2nd and 3rd model')

# Compute sum of activation and diffusion losses
def compute_non_linear_losses(i):
    return  A * np.log(i/io) - B * np.log(1 - i/iLim)

def get_pwfl_breakpoints(x, y, number_of_line_segments):
    # import libraries
    import pwlf
    # initialize piecewise linear fit with your x and y data
    my_pwlf = pwlf.PiecewiseLinFit(x, y)
    # fit the data for the number of line segments
    res = my_pwlf.fitfast(number_of_line_segments)
    return res

iLinspace = np.linspace(10*io, iLim/1.05, int(1e4))
non_linear_losses = compute_non_linear_losses(iLinspace)
iBreakpoints = get_pwfl_breakpoints(iLinspace, non_linear_losses, 11)
vBreakpoints = compute_non_linear_losses(iBreakpoints)

fig, ax = plt.subplots()
ax.plot(iLinspace, non_linear_losses, color='darkblue', label='non linear model')
ax.plot(iBreakpoints, vBreakpoints, color='orange', linestyle='--', marker='o', markersize=4, label='non linear losses points')
ax.set_title('Activation and Diffusion Voltage Drops')
ax.set_ylabel('Drop voltage (V)')
ax.set_xlabel('Current (A)')
ax.legend()
ax.grid()
plt.show()

# %%###################
# 3- Simba Models
#######################
print('3- Config of Simba Models')

project = ProjectRepository(os.path.join(current_folder , "fuelcell_modeling.jsimba"))
models = [project.GetDesignByName('1-FuelCell-Ccode'),
          project.GetDesignByName('2-FuelCell-PWLresistor'),
          project.GetDesignByName('3-FuelCell-DynamicModel')]

# Fuel cell parameters model 1
print('Set parameters in 1st Model with C-code')
models[0].Circuit.SetVariableValue("Eth", str(Eth))
models[0].Circuit.SetVariableValue("rohm", str(rohm))
models[0].Circuit.SetVariableValue("A", str(A))
models[0].Circuit.SetVariableValue("io", str(io))
models[0].Circuit.SetVariableValue("B", str(B))
models[0].Circuit.SetVariableValue("iLim", str(iLim))
models[0].Circuit.SetVariableValue("ncells", str(1))

# Fuel cell parameters model 2
print('Set parameters in 2nd Model with PWL resistor')
models[1].Circuit.SetVariableValue("Eth", str(Eth))
models[1].Circuit.SetVariableValue("rohm", str(rohm))
Rd = models[1].Circuit.GetDeviceByName('Rd')
Rd.VoltageCurrentMatrix = np.vstack((vBreakpoints, iBreakpoints)).T.tolist()

# Fuel cell parameters model 3
print('Set parameters in 3rd Model : Dynamic')
models[2].Circuit.SetVariableValue("Eth", str(Eth))
models[2].Circuit.SetVariableValue("rohm", str(rohm))
models[2].Circuit.SetVariableValue("CdL", str(CdL))
Rd = models[2].Circuit.GetDeviceByName('Rd')
Rd.VoltageCurrentMatrix = np.vstack((vBreakpoints, iBreakpoints)).T.tolist()

project.Save()


# %%###################
# 4- Simulation
#######################
print('4- Simulation')

jobs = []
for model in models:
    jobs.append(model.TransientAnalysis.NewJob())
    status = jobs[-1].Run()
    if str(status) != "OK": 
        print(jobs[-1].Summary()[:-1])
    print("Elapsed time: {:0.2f}s".format(jobs[-1].get_RunTime()))


# %%###################
# 5- Plot vi curves
#######################
print('5- Plot vi curves')

from bokeh.plotting import figure
from bokeh.io import show, output_notebook

fc_current = []
fc_voltage = []
for job in jobs:
    fc_current.append(job.GetSignalByName('FuelCell - Current').DataPoints)
    fc_voltage.append(job.GetSignalByName('FuelCell - Voltage').DataPoints)

# Plot tooltips
TOOLTIPS = [
    ("index", "$index"),
    ("(t, val)", "($x, $y)"),
    ]

# figure 1
p1 = figure(width = 600, height = 400, 
                             title = 'Fuel Cell Models',
                             x_axis_label = 'current (A)', y_axis_label = 'Voltage (V)',
                             active_drag='box_zoom',
                             tooltips = TOOLTIPS)
p1.line(fc_current[0], fc_voltage[0], color='limegreen', legend_label='C-code')
p1.line(fc_current[1], fc_voltage[1], color='orangered', line_dash= 'dashed', legend_label='PWL resistor')
p1.line(fc_current[2], fc_voltage[2], color='green', line_dash= 'dashed', legend_label='Dynamic Model')

output_notebook()
show(p1)
# %%
