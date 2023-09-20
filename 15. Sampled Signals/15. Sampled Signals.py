"""
Simple example showing how to read and use sampled signals (Multi Time-Steps Solver).

##### Requires aesim.simba version 2023.01.19 or higher #####
"""

#%% Load modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt

#%% Load project
flybackConverter = DesignExamples.DCDC_Flyback()

#%% Add an output voltage probe sampled at 1u 
VP1 = flybackConverter.Circuit.AddDevice("Voltage Probe",50,50);
VP1.Name = "VP1"
VP1.SamplingTime = 1E-6
R1 = flybackConverter.Circuit.GetDeviceByName("R2")
C = flybackConverter.Circuit.AddConnection(R1.P,VP1.P)
for s in VP1.Scopes: s.Enabled = True

#%% Get the job object and solve the system
job = flybackConverter.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
Vout = job.GetSignalByName('R2 - Instantaneous Voltage').DataPoints
sampled_signal = job.GetSignalByName('VP1 - Out')
sampled_signal_data = sampled_signal.DataPoints

print ("len(t): "+ str(len(t)))
print ("len(Vout): "+ str(len(Vout)))
print ("len(sampled_signal_data): "+ str(len(sampled_signal_data))) 

# Vout and sampled_signal_data have different sizes! 
# job.TimePoints cannot be used as time data for sampled signals. 
# Instead, we can reconstruct the time data array from the sampling time.
sampled_signal_time = [sampled_signal.SamplingTime*i for i in range(len(sampled_signal_data))]

#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title(flybackConverter.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(t,Vout, label="original")
ax.plot(sampled_signal_time,sampled_signal_data,label="sampled")
ax.legend()
plt.show()
