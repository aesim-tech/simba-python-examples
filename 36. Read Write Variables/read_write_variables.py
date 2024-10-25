#%% Load modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt

#%% Load project
Thyristor_bridge = DesignExamples.ACDC_3ph_ThyristorBridge()
default_fgrid = Thyristor_bridge.Circuit.GetVariableValue("fgrid")
print('Default value of fgrid = {0} Hz'.format(default_fgrid))

#%% Get the job object and solve the system
job = Thyristor_bridge.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
Vout_signal = job.GetSignalByName('Udc - Instantaneous Voltage')
t = Vout_signal.TimePoints
Vout = Vout_signal.DataPoints


#%% New assignment for "fgrid" value inside the "design variables" window
Thyristor_bridge.Circuit.SetVariableValue("fgrid", str(60))

#%% Get another job2 object and solve the system
job2 = Thyristor_bridge.TransientAnalysis.NewJob()
status = job2.Run()

#%% Get results for the new job2
Vout_signal2 = job2.GetSignalByName('Udc - Instantaneous Voltage')
t2 = Vout_signal2.TimePoints
Vout2 = Vout_signal2.DataPoints

#%% Plot Curve
fig, ax = plt.subplots()
ax.set_title(Thyristor_bridge.Name)
ax.set_ylabel('Vout (V)')
ax.set_xlabel('time (s)')
ax.plot(t,Vout, 'b')
ax.plot(t2,Vout2, 'r')
ax.legend(["fgrid = 50 Hz", "fgrid = 60 Hz"])

plt.show()