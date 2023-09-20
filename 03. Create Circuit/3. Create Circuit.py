#%%  Load required module
from aesim.simba import Design
import matplotlib.pyplot as plt

# Method for printing device pin names.
# This allows the user to see how the device pins can be used in the code. 
def print_pin_names(device):
    print('\n# Pins of {0} device:'.format(device.Name))
    for index, pin in enumerate(device.Pins):
        if pin.Name in dir(device):
            print("  Pin named {0} direct access: #YourDeviceObject#.{0}".format(pin.Name))
        else:
            print("  Pin named {0} access: #YourDeviceObject#.Pins[{1:0}]".format(pin.Name, index))


#%%  Create Design
design = Design()
design.Name = "DC/DC - Buck Converter"
design.TransientAnalysis.TimeStep = 1e-6
design.TransientAnalysis.EndTime = 10e-3
circuit = design.Circuit

#%%  Add devices
V1 = circuit.AddDevice("DC Voltage Source", 2, 6)
V1.Voltage = 50
print_pin_names(V1)

SW1 =circuit.AddDevice("Controlled Switch", 8, 4)
print_pin_names(SW1)

PWM = circuit.AddDevice("Square Wave", 2, 0)
PWM.Frequency = 5000
PWM.DutyCycle = 0.5
PWM.Amplitude = 1
print_pin_names(PWM)

D1 = circuit.AddDevice("Diode", 16, 9)
D1.RotateLeft()
print_pin_names(D1)

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

# Make connections
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
plt.show()
# %%
