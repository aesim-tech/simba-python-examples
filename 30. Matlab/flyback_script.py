#%% Load modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt
import numpy as np

#%% Load project
flybackConverter = DesignExamples.DCDC_Flyback()

#%% Get the job object and solve the system
job = flybackConverter.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
Vout = job.GetSignalByName('R2 - Instantaneous Voltage').DataPoints

result = np.array([t, Vout])  # the time and Vout datas are stored into an array to retrieve datas into Matlab

#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title(flybackConverter.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(t,Vout)
plt.show()
# %%
