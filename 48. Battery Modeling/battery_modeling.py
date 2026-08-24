""" Lithium-ion battery model
based on surface fitting of voltage vs SOD and current rate, with extrapolation to OCV and internal resistance
and from LIR18650 data from https://www.ineltro.ch/media/downloads/SAAItem/45/45958/36e3e7f3-2049-4adb-a2a7-79c654d92915.pdf

Fit a model to the voltage surface, using Tremblay's model from:
Tremblay et al., "Experimental Validation of a Battery Dynamic Model for EV Applications, World Electric Vehicle Journal Vol. 3 , 2009, https://dx.doi.org/10.3390/wevj3020289.
"""
# %%
import os
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from aesim.simba import ProjectRepository


# %%####################
# 1- Extract parameters
########################

# Define the voltage model as a function of SOD and current rate, with the parameters to be fitted
def get_battery_voltage(XY, Eo, A, B, K, Rint):
    sod, current = XY
    soc = 1 - sod
    soc_limit = 0.005
    ocv = Eo + A * np.exp(-B * (1 - soc)) - K * (1 / (soc + soc_limit) - 1)
    return ocv - Rint * current - K / (soc + soc_limit) * current


import battery_data_LIR18650 as battery_data

Rint_nom = battery_data.Rint_nom    # nominal internal resistance
Q = battery_data.Q                  # battery capacity in Ah
ncells = 1                          # number of cells in series

min_param = [2, 1e-9, 1e-9, 1e-9, 1e-6] # lower bounds for E0, A, B, K, Rint
max_param = [4.1, 1, 40, 1, 1] # upper bounds for E0, A, B, K, Rint

# %% Only one discharge curve is first considered
rate = 0.5
sod, voltage = battery_data.get_current_rate_data(rate)  # get SOD and voltage data for 0.5C discharge
current = rate * Q * np.ones_like(sod)  # constant current rate of 0.5C

[Eo, A, B, K, Rint], pcov, infodict, msg, _ = curve_fit(get_battery_voltage, (sod, current), voltage, bounds=(min_param, max_param), full_output=True)
perr = np.sqrt(np.diag(pcov))  # standard deviation error on the parameters
residuals = infodict['fvec']
residual_error = np.sqrt(np.sum(residuals**2) / len(residuals))  # residual error

print("\n---- Fitting Tremblay's model to 1 discharge curve @0.5C ----")
print("\n" + msg)
print("\nResults summary:")
print("-----------------")
print(f"Residual error: {residual_error:.3e}")
print("\nFitted parameters:")
print(f"  Eo   = {Eo:8.4f} V")
print(f"  A    = {A:8.6f}")
print(f"  B    = {B:8.4f}")
print(f"  K    = {K:12.6e}")
print(f"  Rint = {Rint:8.6f} Ω")

fig, ax = plt.subplots()
ax.scatter(sod, voltage, color='black', alpha=0.6)
ax.plot(sod, get_battery_voltage((sod, current), Eo, A, B, K, Rint), color='red', label='Fitted model')
ax.set_xlabel('SOD')
ax.set_ylabel('Voltage (V)')
ax.set_title('Tremblay\'s model vs 1 discharge curve @0.5C')
ax.grid()
plt.show()

# %% All discharge curves are considered for surface fitting  
[data_sod_flatten, data_current_rate_flatten, data_volt_flatten] = battery_data.get_all_discharge_data_flattened()
current_rates = battery_data.current_rates

[Eo, A, B, K, Rint], pcov, infodict, msg, _ = curve_fit(get_battery_voltage, (data_sod_flatten, data_current_rate_flatten * Q), data_volt_flatten, bounds = (min_param, max_param), full_output=True)
perr = np.sqrt(np.diag(pcov))  # standard deviation error on the parameters
residuals = infodict['fvec']
residual_error = np.sqrt(np.sum(residuals**2) / len(residuals))  # residual error

print("\n---- Fitting Tremblay's model to all discharge curves ----")
print("\n" + msg)
print("\nResults summary:")
print("-----------------")
print(f"Residual error: {residual_error:.3e}")
print("\nFitted parameters:")
print(f"  Eo   = {Eo:3.3f} V")
print(f"  A    = {A:3.3f}")
print(f"  B    = {B:3.3f}")
print(f"  K    = {K:3.2e}")
print(f"  Rint = {Rint:3.3f} Ω")
print("\nStd. deviation on parameters:")
print(f"  Eo   = {perr[0]:3.4f}")
print(f"  A    = {perr[1]:3.6f}")
print(f"  B    = {perr[2]:3.4f}")
print(f"  K    = {perr[3]:3.6f}")


sod = np.linspace(0, 1, 100)
mesh_sod, mesh_current_rate = np.meshgrid(sod, current_rates, indexing='ij')
mesh_voltage = np.zeros(mesh_current_rate.shape)
mesh_voltage_model = get_battery_voltage((mesh_sod, mesh_current_rate * Q), Eo, A, B, K, Rint)
fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
ax.scatter(data_sod_flatten, data_current_rate_flatten, data_volt_flatten, color='black', alpha=0.6)
ax.plot_surface(mesh_sod, mesh_current_rate, mesh_voltage_model, alpha=0.5, cmap='viridis')
ax.set_xlabel('SOD')
ax.set_ylabel('Current rate (C)')
ax.set_zlabel('Voltage (V)')
ax.set_title('Tremblay\'sModel vs discharge curves')
plt.show()


# %%##################
# 2- Simba Model
######################


current_folder = os.path.dirname(os.path.abspath(__file__))
project = ProjectRepository(os.path.join(current_folder, "battery_modeling.jsimba"))
design = project.GetDesignByName('Design 1')

model = design.Circuit.GetDeviceByName('Batt-1')
model.SetVariableValue("Eo", f"{Eo:3.3f}")
model.SetVariableValue("K", f"{K:3.2e}")
model.SetVariableValue("Q", f"{Q:3.3f}")
model.SetVariableValue("A", f"{A:3.3f}")
model.SetVariableValue("B", f"{B:3.3f}")
model.SetVariableValue("Rint", f"{Rint:3.3f}")
model.SetVariableValue("soc_init", str(1))
model.SetVariableValue("ncells", str(ncells))

jobs = []
current_rates = [0.5, 1, 2, 3]  # C-rates for simulation
for current_rate in current_rates:
    design.Circuit.GetDeviceByName('iBatt').Current = current_rate * Q
    design.TransientAnalysis.EndTime = 3600 / current_rate  # simulation time in seconds for full discharge
    design.TransientAnalysis.FixedTimeStep = True
    design.TransientAnalysis.TimeStep = 10
    jobs.append(design.TransientAnalysis.NewJob())
    status = jobs[-1].Run()
    if str(status) != "OK": 
        print(jobs[-1].Summary()[:-1])
    print("Elapsed time: {:0.2f}s".format(jobs[-1].get_RunTime()))

batt_sod = []
batt_voltages = []
for job in jobs:
    socs = job.GetSignalByName('soc').DataPoints
    batt_sod.append([1 - soc for soc in socs])
    batt_voltages.append(job.GetSignalByName('Vbatt').DataPoints)

fig, ax = plt.subplots()
for i, current_rate in enumerate(current_rates):
    ax.plot(batt_sod[i], batt_voltages[i], label=f'{current_rate}C')
    tmp_sod, tmp_voltage = battery_data.get_current_rate_data(current_rate)
    ax.scatter(tmp_sod, tmp_voltage, color='black', alpha=0.6)

ax.set_xlabel('SOD')
ax.set_ylabel('Voltage (V)')
ax.set_title('SIMBA\'s model vs Data')
ax.legend()
plt.show()

#project.Save()