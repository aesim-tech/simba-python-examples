# Load modules
from aesim.simba import DesignExamples, ProjectRepository
import matplotlib.pyplot as plt
import os

# Load SIMBA project
# DAB = DesignExamples.DCDC_Dual_Active_Bridge_Converter()
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "dcdc_dual_active_bridge_converter.jsimba")
project = ProjectRepository(file_path)
DAB = project.GetDesignByName('DAB') # patch waiting April version and update of DAB example

# Get the job object and solve the system
job = DAB.TransientAnalysis.NewJob()
status = job.Run()
if str(status) != 'OK':
    print(job.Summary())

# Get results
t = job.TimePoints
Vout = job.GetSignalByName('R2 - Voltage').DataPoints

# create and export results into csv file
file = open('Output_voltage.csv', 'w')
for time,line in zip(t,Vout):
    file.write(str(time) + "," + str(line)+ "\n")
file.close()

# Plot figure with graph

fig, ax = plt.subplots()
ax.set_title(DAB.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(t,Vout)
ax.legend(["R2 voltage"])
fig.tight_layout()
plt.show()
