#%% Load modules
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# %% ###################
# Load dataframe       #
########################
print("Load dataframe")

script_folder = os.path.realpath(os.path.dirname(__file__))
filename = "mod_strat_motor_drive_2024-04-11"
df = pd.read_pickle(os.path.join(script_folder, filename + ".pkl" ))

torque_refs = [250, 20]
speed_refs = set(df['speed'])
modulations = set(df['modulation'])
switching_frequencies = set(df['fpwm'])

# %% ###################
# Plot bargraphs       #
########################
print ("Plot bargraphs")

# X-axis Data values/class
loss_types = ["MOS Conduction", "MOS Switching", "PMSM Copper", "PMSM Iron"]

# Graph construction
x_bars = np.arange(len(loss_types))  # the label locations
num_bars = len(switching_frequencies)
width = 1.0/(num_bars+1)  # the width of the bars
"""
the centers of the bars are at positions 0, 1, ..., N-1
the distance between two bars: 1-bar_width
the first bar begins at: 0-bar_width/2
to have an equal spacing between the bar and the left margin as between the bars themselves:
    - the left margin can be set at: 0-bar_width/2-(1-bar_width),
    - similarly, the right margin can be set to: N-1+bar_width/2+(1-bar_width)
"""
left_margin = 0 - width/2 - (1-width)
right_margin = len(loss_types) - 1 + width/2 + (1-width)

fig, axs = plt.subplots(nrows=len(modulations), ncols=len(speed_refs), layout='constrained')
fig.set_size_inches(16, 8)

for op_index, speed_key in enumerate(speed_refs):
    for mod_item_index, mod_key in enumerate(modulations):
        # color constrast for graph construction
        green_color = 0.8   # initial bar color
        multiplier = 0      # shift x position
        ymax = 0            # Y-axis data values
        for fpwm in switching_frequencies:
            df_mask_index = (df['speed']==speed_key) & (df['modulation']==mod_key) & (df['fpwm']==fpwm)
            loss_plot = df.loc[df_mask_index, ['conduction', 'switching', 'copper', 'iron']].values.squeeze()
            ymax_ = np.max(loss_plot)
            ymax = np.max((ymax_, ymax))
            offset = width * multiplier
            bar_plot = axs[mod_item_index, op_index].bar(x_bars + offset, loss_plot, width, label=f"{round(fpwm/1000)} kHz", align='center', color=(0, green_color , 0))
            axs[mod_item_index, op_index].bar_label(bar_plot, padding=3, fontsize=5)
            multiplier += 1
            green_color = green_color - 0.3

        # Add some text for labels, title and custom x-axis tick labels, etc.
        axs[mod_item_index, op_index].set_xlabel('Loss Types', fontsize=8)
        axs[mod_item_index, op_index].set_ylabel('Losses (W)', fontsize=8)
        axs[mod_item_index, op_index].set_title(f'Loss comparison at T = {torque_refs[op_index]} N.m & N = {speed_key} rpm for {mod_key}', fontsize=10)
        axs[mod_item_index, op_index].set_xticks(x_bars + width*(num_bars-1)/2, loss_types)
        axs[mod_item_index, op_index].legend(loc='upper right', ncols=num_bars)
        axs[mod_item_index, op_index].set_ylim(0, ymax*1.25)
        axs[mod_item_index, op_index].grid(visible=True, which="major", axis='y')

fig.tight_layout()

plt.show()

# %% ###################
# Plot histogram       #
########################
print ("Plot histogram")

# Identify the unique combinations of 'speed' and 'modulation'
combinations = df[['speed', 'modulation']].drop_duplicates()

# Calculate the number of subplots needed
n_combinations = len(combinations)
n_cols = len(speed_refs)  # Number of columns in the subplot grid
n_rows = n_combinations // n_cols + (n_combinations % n_cols > 0)  # Calculate rows needed

# plt.figure(figsize=(15, n_rows * n_combinations))
hist_fig, axs = plt.subplots(nrows=n_rows, ncols=n_cols, layout='constrained')
hist_fig.set_size_inches(16, 16)

# Create a subplot for each combination of 'speed' and 'modulation'
for index, (_, row) in enumerate(combinations.iterrows()):
    # plt.subplot(n_rows, n_cols, 2 * index - 1)
    op_index = 0 if row['speed'] == list(speed_refs)[0] else 1
    ax = axs[index % (n_cols+1), op_index]

    # Filter the df for the current combination of speed and modulation
    filtered_data = df[(df['speed'] == row['speed']) & (df['modulation'] == row['modulation'])]
    
    # Plot the histogram of losses for the current combination
    for loss_type in ['conduction', 'switching', 'copper', 'iron']:
        ax.hist(filtered_data['fpwm'], weights=filtered_data[loss_type], bins=20, alpha=0.5, label=loss_type)

    #ax.set_title(f"Speed {row['speed']} rpm, Modulation: {row['modulation']}", fontsize=11)
    ax.set_title(f"T = {torque_refs[op_index]} N.m & N = {row['speed']} rpm for {row['modulation']}", fontsize=11)
    ax.set_xlabel('Switching frequency (Hz)')
    ax.set_ylabel('Losses (W)', fontsize=8)
    ax.legend()

plt.tight_layout(pad = 6)
plt.show()