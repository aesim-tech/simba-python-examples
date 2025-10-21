#%% Load modules
import os
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
import pandas as pd


# %% ###################
# Load dataframe       #
########################
print("Load dataframe")

script_folder = os.path.realpath(os.path.dirname(__file__))
filename = "benchmark_3L_2025-10-21"
df = pd.read_pickle(os.path.join(script_folder, filename + ".pkl" ))

topos = set(df['topo'])


# %% ###################
# Plot bargraphs       #
########################
print ("Plot bargraphs")

# X-axis Data values/class
loss_types = ["Conduction Loss", "Switching Loss", "Junction Temperature"]
x_bars = np.arange(len(loss_types)-1)  # the label locations of conduction and switching losses only

# Graph construction
"""
the centers of the bars are at positions 0, 1, ..., N-1
the distance between two bars: 1 - bar_width
the first bar begins at: 0 - bar_width / 2
to have an equal spacing between the bar and the left margin as between the bars themselves:
    - the left margin can be set at: 0 - bar_width / 2 - (1 - bar_width),
    - similarly, the right margin can be set to: N-1 + bar_width / 2 + (1 - bar_width)
"""
num_bars = 0
for topo in topos:
    num_switch_topo = len(df.loc[(df['topo']==topo), ['conduction']].values.squeeze().tolist().keys())
    num_bars = max(num_switch_topo, num_bars)
width = 0.7 / (num_bars + 1)  # the width of the bars

fig, axs = plt.subplots(nrows=len(topos), ncols=1, constrained_layout=True)
fig.set_size_inches(12, 7)
fig.set_constrained_layout_pads(hspace=0.12)
colors = [cm.cividis(i/5) for i in range(6)]

for topo_index, topo_key in enumerate(topos):
    multiplier = 0          # shift x position
    ax1_ymax = 0            # Y-axis data values axis 1
    ax2_ymax = 0            # Y-axis data values axis 2
    df_mask_index = (df['topo']==topo_key)
    switches = df.loc[df_mask_index, ['conduction']].values.squeeze().tolist().keys()
    ax2 = axs[topo_index].twinx()  # instantiate a second axes that shares the same x-axis
    for switch_index, switch_key in enumerate(switches):
        conduction_loss = df.loc[df_mask_index, ['conduction']].values.squeeze().tolist()[switch_key]
        switching_loss = df.loc[df_mask_index, ['switching']].values.squeeze().tolist()[switch_key]
        temperatures = df.loc[df_mask_index, ['Tj']].values.squeeze().tolist()[switch_key]
        ax1_ymax_ = np.max((conduction_loss, switching_loss))
        ax1_ymax = np.max((ax1_ymax_, ax1_ymax))
        offset = width * multiplier
        bar_plot = axs[topo_index].bar(x_bars + offset, [conduction_loss, switching_loss], width, label=str(switch_key), align='center', color=colors[switch_index], alpha=0.75)
        axs[topo_index].bar_label(bar_plot, padding=3, fontsize=8, fmt='%.2f')
        ax2.bar(len(x_bars)+offset, temperatures, width, align='center', color=colors[switch_index], alpha=0.75)
        ax2.bar_label(ax2.containers[-1], padding=3, fontsize=8, fmt='%.1f')
        ax2_ymax_ = np.max((temperatures))
        ax2_ymax = np.max((ax2_ymax_, ax2_ymax))
        multiplier += 1
    # Add some text for labels, title and custom x-axis tick labels, etc.
    axs[topo_index].set_ylabel('Losses (W)', fontsize=10)
    ax2.set_ylabel('Junction Temperature (°C)', fontsize=10)
    axs[topo_index].set_title(f'{topo_key}', fontsize=11, weight='bold')
    axs[topo_index].set_xticks(np.arange(len(loss_types)) + width*(num_bars-1)/2, loss_types)
    axs[topo_index].legend(loc='upper center', ncols=len(switches), fontsize=7)
    axs[topo_index].set_ylim(0, ax1_ymax*1.35)
    ax2.set_ylim(0, ax2_ymax*1.35)
    axs[topo_index].grid(visible=True, which="major", axis='y', linewidth=0.2, linestyle='--', alpha=0.5)
plt.show()
