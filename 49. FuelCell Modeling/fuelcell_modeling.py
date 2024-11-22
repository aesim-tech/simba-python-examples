"""
Script to compare Fuel Cell Model with C-code and PWL resistor
"""
# %%
import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from aesim.simba import ProjectRepository

# %%###########################
# 1- Fuel Cell Characteristics
###############################

print('1- Fuel Cell Characteristics')

current_folder = os.path.dirname(os.path.abspath(__file__))
data = pd.read_csv(os.path.join(current_folder  , "fuelcell_vi_curve.csv"))
data_current = data['Current (A)'].to_numpy()
data_voltage = data['Voltage (V)'].to_numpy()
ncells = 455
rated_average_cell_voltage = 0.645
Vfuelcell = rated_average_cell_voltage * ncells

# Estimate unknown parameters
Eth = 1.1       # given open-circuit voltage
iLim = 800      # typical limit current (1.5 - 2 A / cm²)
area = 420      # estimated from the limit current (cm²)
CdL = 2.09      # typical double layer capacitor (5 mF / cm²)

def get_fuelcell_voltage(ifc, A, io, B, rohm):
    vfc = Eth - A * np.log(ifc / io) + B * np.log(1 - ifc / iLim) - rohm * ifc
    return vfc

[A, io, B, rohm], _ = curve_fit(get_fuelcell_voltage, data_current, data_voltage, bounds=((1e-9, 1e-9, 1e-9, 1e-6), (1e-1, 1e-1, 1e-1, 1e-2)))
print('A = ', A)
print('io = ', io)
print('B = ', B)
print('rohm =', rohm)

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

# Compute sum of activation and diffusion losses

def compute_non_linear_losses(i):
    return  A * np.log(i/io) - B * np.log(1 - i/iLim)

def get_pwfl_breakpoints(x, y, number_of_line_segments):
    # import libraries
    import pwlf
    from scipy.optimize import minimize
    # initialize piecewise linear fit with your x and y data
    my_pwlf = pwlf.PiecewiseLinFit(x, y)

    # initialize custom optimization
    my_pwlf.use_custom_opt(number_of_line_segments)

    # i have number_of_line_segments - 1 number of variables
    # let's guess the correct location of the two unknown variables
    # (the program defaults to have end segments at x0= min(x) and xn=max(x)
    xGuess = np.linspace(x[1], x[-2], number_of_line_segments-1)

    res = minimize(my_pwlf.fit_with_breaks_opt, xGuess)

    # set up the break point locations
    x0 = np.zeros(number_of_line_segments + 1)
    x0[0] = np.min(x)
    x0[-1] = np.max(x)
    x0[1:-1] = res.x

    # calculate the parameters based on the optimal break point locations
    my_pwlf.fit_with_breaks(x0)

    # predict for the determined points
    xHat = np.linspace(min(x), max(x), num=10000)
    yHat = my_pwlf.predict(xHat)

    return x0, xHat, yHat

iLinspace = np.linspace(10*io, iLim/1.05, int(1e4))
non_linear_losses = compute_non_linear_losses(iLinspace)

[iBreakpoints, _, _] = get_pwfl_breakpoints(iLinspace, non_linear_losses, 11)
non_linear_losses_points = compute_non_linear_losses(iBreakpoints)


fig, ax = plt.subplots()
ax.plot(iLinspace, non_linear_losses, color='darkblue', label='non linear model')
ax.plot(iBreakpoints, non_linear_losses_points, color='orange', linestyle='--', marker='o', markersize=4, label='non linear losses points')
ax.set_title('Activation and Diffusion Voltage Drops')
ax.set_ylabel('Drop voltage (V)')
ax.set_xlabel('Current (A)')
ax.legend()
ax.grid()
plt.show()


# %%###################
# 2- Simba circuits
#######################
print('2- Config of Simba circuits')

project = ProjectRepository(os.path.join(current_folder , "fuelcell_modeling_2024-05.jsimba"))
models = [project.GetDesignByName('1-FuelCell-Ccode'),
          project.GetDesignByName('2-FuelCell-PWLresistor'),
          project.GetDesignByName('3-FuelCell-DynamicModel')]

# Fuel cell parameters model 1
print('Set parameters in 1st Model with C-code')
models[0].Circuit.SetVariableValue("rohm", str(rohm))
models[0].Circuit.SetVariableValue("A", str(A))
models[0].Circuit.SetVariableValue("io", str(io))
models[0].Circuit.SetVariableValue("B", str(B))
models[0].Circuit.SetVariableValue("iLim", str(iLim))

# Fuel cell parameters model 2
print('Set parameters in 2nd Model with PWL resistor')
models[1].Circuit.SetVariableValue("rohm", str(rohm))
Rd = models[1].Circuit.GetDeviceByName('Rd')
Rd.VoltageCurrentMatrix = np.vstack((non_linear_losses_points, iBreakpoints)).T.tolist()

# Fuel cell parameters model 3
print('Set parameters in 3rd Model : Dynamic')
models[2].Circuit.SetVariableValue("rohm", str(rohm))
models[2].Circuit.SetVariableValue("CdL", str(CdL))
Rd = models[2].Circuit.GetDeviceByName('Rd')
Rd.VoltageCurrentMatrix = np.vstack((non_linear_losses_points, iBreakpoints)).T.tolist()

project.Save()


# %%###################
# 3- Simulation
#######################
print('3- Simulation')

jobs = []
for model in models:
    jobs.append(model.TransientAnalysis.NewJob())
    status = jobs[-1].Run()
    if str(status) != "OK": 
        print(jobs[-1].Summary()[:-1])
    print("Elapsed time: {:0.2f}s".format(jobs[-1].get_RunTime()))


# %%###################
# 4- Plot waveforms
#######################
print('4- Plot waveforms')

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
