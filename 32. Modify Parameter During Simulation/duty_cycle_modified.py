#%% Load required module
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt
import numpy as np

#%% Load project
Buck = DesignExamples.BuckConverter()

#%% Enable scopes for R1 
R1= Buck.Circuit.GetDeviceByName('R1')
for scope in R1.Scopes:
    scope.Enabled=True
    
#%% Get the job object and solve the system
Buck.TransientAnalysis.NumberOfPointsToSimulate = 15000 # Emulate the Intermediate Time when change occurs suddenly by using set of points
Buck.TransientAnalysis.StopAtSteadyState=False
job = Buck.TransientAnalysis.NewJob()
PWM=Buck.Circuit.GetDeviceByName('C1')
PWM.DutyCycle=0.5


#%% Run the first simulation
status = job.Run()
print(job.Summary())

#%% Run the simulation following the previous one with a new duty cycle value
PWM.DutyCycle=0.7
status = job.Run()

#%% Get results
Vout_signal = job.GetSignalByName('R1 - Voltage')

#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title(Buck.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(np.array(Vout_signal.TimePoints),np.array(Vout_signal.DataPoints))

plt.show()