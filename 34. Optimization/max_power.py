from aesim.simba import ProjectRepository
import os
import numpy as np
from scipy.optimize import minimize


# Objective function to maximize power
def objective_function(R_load):
    current_folder = os.path.dirname(os.path.abspath(__file__))
    project = ProjectRepository(os.path.join(current_folder , "max_power.jsimba"))
    design = project.GetDesignByName('Design 1')
    design.Circuit.GetDeviceByName('R2').Value = float(R_load[0])
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK": 
        raise Exception(job.Summary())
    Iout = job.GetSignalByName('R2 - Current').DataPoints
    power = Iout[-1]**2*R_load
    project.Save()
    return -power  # Negative sign because we're maximizing


# Initial guess for R_load
initial_guess = np.array([3.4])

# Bounds for R_load
bounds = [(2.5, 3.5)]  # Load resistance should be between 2.5 and 3.5 ohms

# Optimize using the L-BFGS-B method
result = minimize(objective_function, initial_guess, method='L-BFGS-B', bounds=bounds)

# Display the result
optimal_R_load = result.x[0]
max_power = -result.fun  # Convert back to positive power value

print('Optimal R_load = {0:.4f} Ohm'.format(optimal_R_load))
print('Transferred Power P = {0:.4f} W'.format(max_power))
