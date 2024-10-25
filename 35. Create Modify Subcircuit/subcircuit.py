#%% Load modules
from aesim.simba import JsonProjectRepository, Design
import matplotlib.pyplot as plt
import os

#%% Load SIMBA project
script_folder = os.path.realpath(os.path.dirname(__file__))
simba_file_path = os.path.join(script_folder, "subcircuit.jsimba")
project = JsonProjectRepository(simba_file_path)
design1 = project.GetDesignByName('Design1')

#%% New design to create a subcircuit
design2 = Design(design1)                   # creation of a new design object "design2"
project.AddDesign(design2)                  # add design2 to the existing project
design2.Name = "Design 2 with subcircuit"   # give a name to the object design2

# Create subcircuit
subcircuit_content = []
R1 = design2.Circuit.GetDeviceByName("R1")
R2 = design2.Circuit.GetDeviceByName("R2")
segments = design2.Circuit.GetConnectorConnectedTo(R1.N).Segments
subcircuit_content.append(R1)
subcircuit_content.append(R2)
subcircuit_content += segments
design2.Circuit.CreateSubsystem(subcircuit_content)

# Get devices names of design2
print('Devices in main circuit:')
for device in design2.Circuit.Devices:
    print(' - ' + device.Name)

#%% Enter inside a subcircuit
my_subckt = design2.Circuit.GetDeviceByName('Sc1').Definition # Subcircuit access by using "Definition"
my_subckt.Name= "Sub_module" # rename subcircuit name

# Get devices names in subckt
print('Devices in sub-circuit:')
for device in my_subckt.Devices:
    print(' - ' + device.Name)

# Modify a device in the sub-circuit
my_subckt.GetDeviceByName('R2').Value = 6   # new value assignment for R2

# Save project
project.Save()

#%% Get job objects and run simulations
job1 = design1.TransientAnalysis.NewJob()
status = job1.Run()
job2 = design2.TransientAnalysis.NewJob()
status = job2.Run()

# Get signal names of job2
print('Signals got with the simulation of sub-circuit:')
for signal in job2.Signals:
    print(' - ' + signal.get_Name())

# Get results
signal1 = job1.GetSignalByName('R2 - Instantaneous Voltage');
signal2 = job2.GetSignalByName('Sc1:R2 - Instantaneous Voltage')
t1 = signal1.TimePoints
t2 = signal2.TimePoints
Vout1 = signal1.DataPoints  # without subcircuit
Vout2 = signal2.DataPoints  # with subcircuit


#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title("Output voltage depending on Resistor value (R2)")
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(t1,Vout1, 'b')
ax.plot(t2,Vout2, '+r')
ax.legend(["R2 = 3 ohms", "R2 = 6 ohms"])

fig.tight_layout()
plt.show()
# %%