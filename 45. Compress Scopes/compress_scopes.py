"""
Simple example showing how to enable and use the compress scopes feature.

##### Requires aesim.simba version 2024.05 or higher #####
"""

#%% Load modules
from aesim.simba import DesignExamples
import matplotlib.pyplot as plt

flybackConverter = DesignExamples.DCDC_Flyback()

# Add a scope to the square source
C1 = flybackConverter.Circuit.GetDeviceByName("C1")
for scope in C1.Scopes:
    scope.Enabled = True

flybackConverter.TransientAnalysis.EndTime = "40u"
flybackConverter.TransientAnalysis.StopAtSteadyState = False

# Solve the system without compression
job1 = flybackConverter.TransientAnalysis.NewJob()
job1.Run()

# Get results
t_without_compression = job1.TimePoints
Cout_without_compression = job1.GetSignalByName('C1 - Out').DataPoints

# Activate the compression, solve the system again
flybackConverter.TransientAnalysis.CompressScopes = True
job2 = flybackConverter.TransientAnalysis.NewJob()
job2.Run()

# Get results with compression
Cout_signal = job2.GetSignalByName('C1 - Out')
Cout_with_compression = Cout_signal.DataPoints
t_with_compression = Cout_signal.TimePoints

print("len(t_without_compression):", len(t_without_compression))
print("len(t_with_compression):", len(t_with_compression))
print("len(Cout_without_compression):", len(Cout_without_compression))
print("len(Cout_with_compression):", len(Cout_with_compression))

# Plotting the results
fig, ax = plt.subplots()
ax.set_title(flybackConverter.Name)
ax.set_ylabel('Cout')
ax.set_xlabel('time (s)')
ax.plot(t_without_compression, Cout_without_compression, '-+', label="original")
ax.plot(t_with_compression, Cout_with_compression, '+', label="compressed")
ax.legend()
plt.show()