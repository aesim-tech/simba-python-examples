#%% Load modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt
import numpy as np

#%% Load project
flybackConverter = DesignExamples.DCDC_Flyback()
flybackConverter.TransientAnalysis.CompressScopes = True

#%% Get the job object and solve the system
job = flybackConverter.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
R2_signal = job.GetSignalByName('R2 - Instantaneous Voltage') 
t = R2_signal.TimePoints
vout = R2_signal.DataPoints

result = np.array([t, vout])  # compressed time and vout data are stored into an array to be sent to Matlab
