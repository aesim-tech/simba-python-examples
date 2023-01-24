#%%  Load required module
import matplotlib.pyplot as plt
from aesim.simba import Design, ProjectRepository
import os, pathlib

#%%  Create Simple Design
design = Design()
design.Name = "DC/DC - Buck Converter"
design.TransientAnalysis.TimeStep = 1e-6
design.TransientAnalysis.EndTime = 10e-3
circuit = design.Circuit
V1 = circuit.AddDevice("DC Voltage Source", 2, 6)
V1.Voltage = 50
SW1 =circuit.AddDevice("Controlled Switch", 8, 4)
PWM = circuit.AddDevice("Square Wave", 2, 0)
PWM.Frequency = 5000
PWM.DutyCycle = 0.5
PWM.Amplitude = 1
D1 = circuit.AddDevice("Diode", 16, 9)
D1.RotateLeft()
L1 = circuit.AddDevice("Inductor", 20, 5)
L1.Value = 1E-3
C1 = circuit.AddDevice("Capacitor", 28, 9)
C1.RotateRight()
C1.Value = 100E-6
R1 = circuit.AddDevice("Resistor", 34, 9)
R1.RotateRight()
R1.Value = 5
R1.Name = "R1"
for scope in R1.Scopes:
    scope.Enabled = True
g = circuit.AddDevice("Ground", 3, 14) 
circuit.AddConnection(V1.P, SW1.P)
circuit.AddConnection(SW1.N, D1.Cathode)
circuit.AddConnection(D1.Cathode, L1.P)
circuit.AddConnection(L1.N, C1.P)
circuit.AddConnection(L1.N, R1.P)
circuit.AddConnection(PWM.Out, SW1.In)
circuit.AddConnection(V1.N, g.Pin)
circuit.AddConnection(D1.Anode, g.Pin)
circuit.AddConnection(C1.N, g.Pin)
circuit.AddConnection(R1.N, g.Pin)

#%%  Save Design in Project File
filepath = os.path.join(pathlib.Path().absolute(), "Buck Converter.jsimba")
if(os.path.isfile(filepath)): os.remove(filepath) # Remove file if it already exists
project = ProjectRepository(filepath) # Create project file if it doesn't exist.
project.AddDesign(design)
project.Save()

#%%  Open Design
project2 = ProjectRepository(filepath) # Open file
design = project2.GetDesignByName("DC/DC - Buck Converter")

#%%  Run Simulation
job = design.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
Vout = job.GetSignalByName('R1 - Instantaneous Voltage').DataPoints

#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title(design.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(t,Vout)

# %%
