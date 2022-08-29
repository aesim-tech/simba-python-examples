# Example of simulation where parameters are modified while a simulation is ongoing. 

#%% Load modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt

#%% Load project and get R2 and C2 devices
flybackConverter = DesignExamples.DCDC_Flyback()
R2 = flybackConverter.Circuit.GetDeviceByName("R2")
C1 = flybackConverter.Circuit.GetDeviceByName("C1")

#%% Get the job object and solve the system
flybackConverter.TransientAnalysis.NumberOfPointsToSimulate = 30000
flybackConverter.TransientAnalysis.StopAtSteadyState = False
job = flybackConverter.TransientAnalysis.NewJob()
status = job.Run()
print("Initial End Time: {endTime} ms status:{status} Number Of Points:{n}".format(endTime = job.TimePoints[-1]*1000, status=status, n = len(job.TimePoints)))

#%% Clear all scopes and run simulation again
R2.Value = 2
status = job.Run()
print("Second End Time: {endTime} ms status:{status} Number Of Points:{n}".format(endTime = job.TimePoints[-1]*1000, status=status, n = len(job.TimePoints)))

#%% Clear all scopes before 1ms
job.ClearScopesData(1E-3);

#%%  Run Simulation again
C1.Value =100E-6
status = job.Run()
print("Final End Time: {endTime} ms status:{status} Number Of Points:{n}".format(endTime = job.TimePoints[-1]*1000, status=status, n = len(job.TimePoints)))

#%% Plot Curve
t = job.TimePoints
Vout = job.GetSignalByName('R2 - Instantaneous Voltage').DataPoints
fig, ax = plt.subplots()
ax.plot(t,Vout)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('Time (s)')

