#%% Load modules
import os
from aesim.simba import ProjectRepository
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


#%% Define topologies, switches and result dataframes

# topos = ['3L-NPC', '3L-T-type', '3L-FC']
topos = ['3L-NPC', '3L-T-type']
switches = dict()
switches['3L-NPC'] = ['T1', 'T2', 'D1', 'D2', 'D5']
switches['3L-T-type'] = ['T1', 'T2', 'T3', 'D1', 'D2', 'D3']
switches['3L-FC'] = ['T1', 'T2', 'D1', 'D2']
all_switches = list(set(switches['3L-NPC'] + switches['3L-T-type'] + switches['3L-FC']))


# Waveforms
waveforms_df = pd.DataFrame([], columns=topos, index=['U12', 'iL1', 'iL2', 'iL3'])
# Losses
conduction_loss_df = pd.DataFrame([], columns=topos, index=all_switches)
switching_loss_df = conduction_loss_df.copy(deep=True)
Tj_df = conduction_loss_df.copy(deep=True)

#%% Load simba project
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "benchmark_3L_3ph_inverters.jsimba")
project = ProjectRepository(file_path)

#%% Run simulation for each topology and collect results
for topo in topos:
    design = project.GetDesignByName(topo)
    design.Circuit.SetVariableValue('ma', str(0.8))
    design.TransientAnalysis.EndTime = 0.04
    design.TransientAnalysis.TimeStep = 1e-6
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK": 
        print (job.Summary())
    for s in all_switches:
        if s in switches[topo]:
            conduction_loss_df.at[topo, s] = job.GetSignalByName(s + ' - Average Conduction Losses (W)').DataPoints[-1]
            switching_loss_df.at[topo, s] = job.GetSignalByName(s + ' - Average Switching Losses (W)').DataPoints[-1]
            # if topo == '3L-T-type' and s == 'T3':
            #    print('debug T3 Tj')
            Tj_df.at[topo, s] = job.GetSignalByName(s + ' - Junction Temperature (°)')
        else:
            conduction_loss_df.at[topo, s] = np.nan
            switching_loss_df.at[topo, s] = np.nan
            Tj_df.at[topo, s] = np.nan
    waveforms_df.at[topo, 'U12'] = job.GetSignalByName('U12 - Voltage')
    for k in range(1, 4):
        waveforms_df.at[topo, 'iL'+str(k)] = job.GetSignalByName('L' + str(k) + ' - Current')

#%% Plot results
fig, axs = plt.subplots(nrows=2, ncols=1, layout='constrained')
axs[0].plot(waveforms_df.loc['3L-NPC', 'U12'].TimePoints, waveforms_df.loc['3L-NPC','U12'].DataPoints, label='U12 (V)')
for k in range(1, 4):
    axs[1].plot(waveforms_df.loc['3L-NPC', 'iL'+str(k)].TimePoints, waveforms_df.loc['3L-NPC','iL'+str(k)].DataPoints, label='iL' + str(k))
axs[1].set_xlabel('Time (s)')
axs[0].set_ylabel('U12 (V)')
axs[0].grid()
axs[1].set_ylabel('Currents (A)')
axs[1].grid()
axs[1].legend()

#%%
n_rows = len(topos)
hist_fig, axs = plt.subplots(nrows=n_rows, ncols=1, layout='constrained')
hist_fig.set_size_inches(16, 16)

axs

for index in range(n_rows):
    topo = topos[index]
    ax = axs[index]
    for s in switches[topo]:
        ax.hist(conduction_loss_df.loc[topo, s].dropna(), bins=10, alpha=0.5, label=s)
    ax.hist(switching_loss_df.loc[topo].dropna(), bins=10, alpha=0.5, label='Switching Losses (W)')
    ax.set_title(f'Loss Distribution for {topo}')
    ax.legend()
#%%
