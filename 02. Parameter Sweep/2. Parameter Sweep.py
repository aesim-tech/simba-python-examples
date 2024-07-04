#%% Load required modules
import matplotlib.pyplot as plt
import numpy as np
from aesim.simba import DesignExamples

#%% Calculating Vout=f(dutycycle)
BuckBoostConverter = DesignExamples.BuckBoostConverter()
dutycycles = np.arange(0.00, 0.9, 0.9/30)
Vouts = []
for dutycycle in dutycycles:
    # Set duty cycle value
    PWM = BuckBoostConverter.Circuit.GetDeviceByName('C1')
    PWM.DutyCycle=dutycycle
    
    # Run calculation
    job = BuckBoostConverter.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK": 
        raise Exception(job.Summary())

    # Retrieve results
    t = np.array(job.TimePoints)
    Vout = np.array(job.GetSignalByName('Rload - Voltage').DataPoints)

    # Average output voltage for t > 5ms
    indices = np.where(t >= 0.005)
    Vout = np.take(Vout, indices)
    Vout = np.average(Vout)
    
    # Save results
    Vouts.append(Vout)

#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title(BuckBoostConverter.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('Duty Cycle')
ax.plot(dutycycles,Vouts)
plt.show()