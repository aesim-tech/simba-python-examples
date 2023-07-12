#%% Load modules
from aesim.simba import JsonProjectRepository
import matplotlib.pyplot as plt
import os 
import numpy as np

script_folder = os.path.realpath(os.path.dirname(__file__))
csv_filename = script_folder + '/ArtUrban.csv'
csv_file = open(csv_filename)

#%% First way: with csv module
import csv
time = []
speed = []
for kLine, line in enumerate(csv.reader(csv_file)):
    if kLine == 0:
        xlabel = line[0]
        ylabel = line[1]
    if kLine > 0:
        time.append(float(line[0]))
        speed.append(float(line[1]))

fig = plt.figure()
plt.plot(time, speed)
plt.xlabel(xlabel)
plt.ylabel(ylabel)
plt.title('ArtUrban drive cycle extracted with CSV reader')
plt.show()

#%% Second way: with pandas module
import pandas as pd
df = pd.read_csv(csv_filename)
time = df['time (s)'].to_numpy()
speed = df['speed (km/h)'].to_numpy()

fig = plt.figure()
plt.plot(time, speed, 'g')
plt.xlabel(df.columns[0])
plt.ylabel(df.columns[1])
plt.title('ArtUrban drive cycle extracted with Pandas')
plt.show()




# %%
speed_ms = speed * 1e3 / 3600
acceleration = np.diff(speed_ms) / np.diff(time)
acceleration = np.insert(acceleration, 0, 0)

mass = 2057    # mass (kg)
a = 178.7      # rolling resistance on flat land (N)
b = 3.3084     # compononent of the rolling resistance (N / (m / s))
c = 0.5231952  # aerodynamic drag (N / (m / s²))
tractive_force = acceleration * mass + a + b * speed + c * speed**2

fig = plt.figure()
plt.plot(time, tractive_force, 'g')
plt.xlabel('time (s)')
plt.ylabel('tractive force (N)')
plt.title('Tractive force computed with data **')
plt.show()
      
# %%
