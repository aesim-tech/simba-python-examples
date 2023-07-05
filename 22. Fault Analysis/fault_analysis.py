#%% Load modules
from aesim.simba import JsonProjectRepository
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import numpy as np


#%% Load SIMBA project
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "fault_analysis.jsimba")
project = JsonProjectRepository(file_path)
RLC = project.GetDesignByName('RLC')

#%% Nominal case
job = RLC.TransientAnalysis.NewJob()
status = job.Run()
tnom = job.TimePoints
vout_nom = job.GetSignalByName('R2 - Voltage').DataPoints

vout_nom_max = max(vout_nom)
vout_nom_final = vout_nom[-1]
overshoot_nom = vout_nom_max - vout_nom_final

#%% Fault case: short circuit accross R1
R1 = RLC.Circuit.GetDeviceByName('R1')
RLC.Circuit.AddConnection(R1.P, R1.N)
job = RLC.TransientAnalysis.NewJob()
status = job.Run()
tfault = job.TimePoints
Vout_fault = job.GetSignalByName('R2 - Voltage').DataPoints

vout_fault_max = max(Vout_fault)
vout_fault_final = Vout_fault[-1]
overshoot_R1 = vout_fault_max - vout_fault_final


#%% Set test case
if overshoot_R1 > overshoot_nom:
    status = "Status = WARNING: overshoot with fault case is greater than nominal overshoot value and is equal to {0:2f} V".format(overshoot_R1)
else: 
    status = "Status = OK:  Overshoot with fault case is below the nominal value"

#%% Write report
report_start = ('\n################################\n' +
                '# Fault Analysis Report \n' +
                '# Date: ' + datetime.now().strftime("%m-%d-%Y \n# Hour: %H:%M:%S") + "\n" +
                '################################\n\n'
                "# Nominal case:\n  Vout_max = {0:.2f} V - Vout_final = {1:.2f} V - overshoot = {2:.2f} V \n".format(vout_nom_max, vout_nom_final, overshoot_nom) +
                "# Fault case:\n  Vout_max = {0:.2f} V - Vout_final = {1:.2f} V - overshoot = {2:.2f} V \n".format(vout_fault_max, vout_fault_final, overshoot_R1))
report_to_print = '\n'.join([report_start, status])
print(report_to_print)
file = open(script_folder + '/report' + datetime.now().strftime("%m%d%Y%H%M") + '.txt', 'w')
file.write(report_to_print)
file.close()

#%% Plot figures
mpl.rcParams['font.size'] = 15  # Set the default font 
fig = plt.figure(figsize = (16, 9))
plt.plot(tnom, vout_nom, "g")
plt.plot(tfault, Vout_fault, "r")

plt.xlabel('time')
plt.ylabel('vout_nominal')
plt.title("nominal output voltage")

fig.tight_layout()
plt.show()