# Load modules
from aesim.simba import DesignExamples, ProjectRepository
import matplotlib.pyplot as plt
import os

# Load SIMBA project
DAB = DesignExamples.DCDC_Dual_Active_Bridge_Converter()

# Get the job object and solve the system
job = DAB.TransientAnalysis.NewJob()
status = job.Run()
if str(status) != 'OK':
    print(job.Summary())

# Get results
Vout_signal = job.GetSignalByName('R2 - Voltage')
t = Vout_signal.TimePoints
Vout = Vout_signal.DataPoints

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
