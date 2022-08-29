#%% Load modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt

#%% Load project
flybackConverter = DesignExamples.DCDC_Flyback()

#%% Get the job object and solve the system
job = flybackConverter.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
Vout = job.GetSignalByName('R2 - Instantaneous Voltage').DataPoints

#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title(flybackConverter.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(t,Vout)

# %%
