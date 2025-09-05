#%% Load modules
import os
from aesim.simba import ProjectRepository
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


##% ###################


script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "benchmark_3L_3ph_inverters.jsimba")
project = ProjectRepository(file_path)

npc_design = project.GetDesignByName('3L-NPC')

job = npc_design.TransientAnalysis.NewJob()
status = job.Run()
if str(status) != "OK": 
    print (job.Summary())

npc_switches = ['T1', 'T2', 'D1', 'D2', 'D5']
ttype_switches = ['T1', 'T2', 'T3', 'D1', 'D2', 'D3']
fc_switches = ['T1', 'T2', 'D1', 'D2']

topos = ['3L-NPC', '3L-T-type', '3L-FC']
switches = list(set(npc_switches + ttype_switches + fc_switches))
# Waveforms
u12 = job.GetSignalByName('U12 - Voltage (V)')
iL = []
for k in range(1, 3):
    iL.append(job.GetSignalByName('L' + str(k) + ' - Current (A)'))


# Junction temperatures
Tj = []
for switch in npc_switches:
    Tj.append(job.GetSignalByName(switch + ' - Junction Temperature (C)'))
    
# Losses
conduction_loss_df = pd.DataFrame([], columns=topos, index=switches)
switching_loss_df = conduction_loss_df.copy()

# Junction temperatures
Tj_df = pd.DataFrame({'topology': ['3L-NPC', '3L-T-type', '3L-FC'],
                                   'T1': [],
                                   'T2': [],
                                   'D1': [],
                                   'D2': [],
                                   'T3': [],
                                   'D3': [],
                                   'D5': []})
switching_losses
for switch in npc_switches:
    conduction_losses.append = sum([job.GetSignalByName('T' + str(n) + ' - Average Conduction Losses (W)').DataPoints[-1] for n in range(1, 7)])
    switching_losses = sum([job.GetSignalByName('T' + str(n) + ' - Average Switching Losses (W)').DataPoints[-1] for n in range(1, 7)])

