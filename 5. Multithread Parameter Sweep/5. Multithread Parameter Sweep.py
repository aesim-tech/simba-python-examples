# %% Load required modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt
import numpy as np, threading

def run_job(job, Vouts, index):
    # Start job
    job.Run()

    # Retrieve results
    t = np.array(job.TimePoints)
    Vout = np.array(job.GetSignalByName('R1 - Instantaneous Voltage').DataPoints)

    # Average output voltage for t > 2ms
    indices = np.where(t >= 0.002)
    Vout = np.take(Vout, indices)

    # Save Voltage in Vouts
    Vouts[index] = np.average(Vout)

# %% Get the result object and solve the system
BuckBoostConverter = DesignExamples.BuckBoostConverter()
numberOfPoints = 50
dutycycles = np.arange(0.00, 0.9, 0.9/numberOfPoints)
Vouts = [None] * numberOfPoints
threads = [None] * numberOfPoints

for i in range(len(dutycycles)):
    # Set duty cycle value
    PWM = BuckBoostConverter.Circuit.GetDeviceByName('C1')
    PWM.DutyCycle = dutycycles[i]

    # Run calculation in separate thread
    job = BuckBoostConverter.TransientAnalysis.NewJob()
    threads[i] = threading.Thread(target=run_job, args=(job, Vouts, i))
    threads[i].start()

# Wait for all calculation to finish
for thread in threads:
    thread.join()

# %% Plot Curve
fig, ax = plt.subplots()
ax.set_title(BuckBoostConverter.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('Duty Cycle')
ax.plot(dutycycles, Vouts)

# %%
