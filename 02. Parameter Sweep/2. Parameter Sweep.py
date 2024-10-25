#%% Load required modules
import matplotlib.pyplot as plt
import numpy as np
from aesim.simba import DesignExamples

#%% Calculating Vout=f(dutycycle)
BuckBoostConverter = DesignExamples.BuckBoostConverter()
dutycycles = np.arange(0.00, 0.9, 0.9/30).tolist()
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
    Vout_signal = job.GetSignalByName('Rload - Voltage')
    t = np.array(Vout_signal.TimePoints)
    Vout = np.array(Vout_signal.DataPoints)

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