#%% Load modules
import scipy.io as sio
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import os

#%% Load mat file
script_folder = os.path.realpath(os.path.dirname(__file__))
contents = sio.loadmat(script_folder + '/DriveCycles/all_drive_cycles.mat')
drive_cycles = dict()    # create dict to store drive cycles
for key in contents.keys():
    if isinstance(contents[key], np.ndarray):
        drive_cycles[key] = contents[key]

#%% Plot all drive cycles
mpl.rcParams['font.size'] = 8  # Set the default font 
fig = plt.figure()
nb_subplots = int(np.ceil(len(drive_cycles) / 3))
count = 0
for key in drive_cycles.keys():
    count = count + 1
    plt.subplot(nb_subplots, 3, count)
    plt.plot(drive_cycles[key][:, 0], drive_cycles[key][:, 1])
    plt.xlabel('time (s)')
    plt.ylabel('speed (km / h)')
    plt.title(key)
fig.tight_layout(pad=0)
plt.show()

#%% Option to write cvs files 
write_csv_files = False
if write_csv_files:
    import pandas as pd
    for key in drive_cycles.keys():
        df = pd.DataFrame(drive_cycles[key], columns = ['time (s)', 'speed (km/h)'])
        df.to_csv(script_folder + '/DriveCycles/' + key + '.csv', index = False)