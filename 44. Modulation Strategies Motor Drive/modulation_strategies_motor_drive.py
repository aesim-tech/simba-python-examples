#%% Load modules
from aesim.simba import ProjectRepository
import matplotlib.pyplot as plt
import os
import numpy as np


# Get project
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "modulation_strategies_motor_drive.jsimba")
project = ProjectRepository(file_path)

# Dictionary containing each design
modulation_dict = {"SVPWM": project.GetDesignByName('SVPWM_modulation'),
              "DPWM": project.GetDesignByName('DPWM_modulation'),
              "SPWM": project.GetDesignByName('SPWM_modulation'),
              }
# Switching frequencies and Speed definition 
switching_frequencies = [2e4, 4e4, 6e4]
rpm_speeds = [2000, 4000]

# Id, Iq & Torque definition for different Speeds
Id_dict = {2000:-157.47, 4000:-19.32}
Iq_dict = {2000:157.03, 4000:11.52}
torque_dict = {2000:250, 4000:20}

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

fig, axs = plt.subplots(nrows=len(modulation_dict), ncols=len(rpm_speeds), layout='constrained')
fig.set_size_inches(16, 9)

# Sweep of operating points for each design    
for mod_item_index, (keyname, design) in enumerate(modulation_dict.items()):   # modulation strategy loop
    motor = design.Circuit.GetDeviceByName('JmagRTMotor')
    motor.RttFilePath.UserValue = os.path.join(script_folder, 'withHF_4000rpm20Nm.rtt')

    print('***************** speed', rpm_speeds, 'circuit:', keyname)

    for rpm_index, rpm in enumerate(rpm_speeds):   # rpm speed loop
        
        # Set rpm value
        speed_source_rads = design.Circuit.GetDeviceByName('W1')
        speed_source_rads.Voltage = (rpm*np.pi/30)

        # Id & Iq are set for each Speed swept
        Id_ref = design.Circuit.GetDeviceByName('Id_ref')
        Id_ref.Value = Id_dict[rpm]
        Iq_ref = design.Circuit.GetDeviceByName('Iq_ref')
        Iq_ref.Value = Iq_dict[rpm]

        # color constrast for graph construction
        green_color = 0.8   # initial bar color
        multiplier = 0      # shift x position
        ymax = 0            # Y-axis data values

        Carrier = design.Circuit.GetDeviceByName('Carrier')
        for fpwm in switching_frequencies:   # fpwm loop
            
            # Set fpwm value
            Carrier.Frequency = fpwm
            
            # Run calculation
            job = design.TransientAnalysis.NewJob()
            status = job.Run()
            if str(status) != "OK": 
                print (job.Summary()[:-1])

            # Inverter Losses
            conduction_losses = sum([job.GetSignalByName('T' + str(n) + ' - Average Conduction Losses (W)').DataPoints[-1] for n in range(1, 7)])
            switching_losses = sum([job.GetSignalByName('T' + str(n) + ' - Average Switching Losses (W)').DataPoints[-1] for n in range(1, 7)])
                                        
            # Motor losses
            copper_losses = job.GetSignalByName('JmagRTMotor - Copper Loss (average)').DataPoints[-1] 
            iron_losses = job.GetSignalByName('JmagRTMotor - Iron Loss (average)').DataPoints[-1] 
            print(f"Check speed = {rpm} rpm for circuit <{keyname}> - {round(fpwm/1000)} kHz", conduction_losses, switching_losses, copper_losses, iron_losses)

            # Plot Curve
            loss_results = [conduction_losses, switching_losses, copper_losses, iron_losses]
            ymax_ = np.max(loss_results)
            ymax = np.max((ymax_, ymax))
            offset = width * multiplier
            bar_plot = axs[mod_item_index, rpm_index].bar(x_bars + offset, loss_results, width, label=f"{round(fpwm/1000)}KHz", align='center', color=(0, green_color , 0))
            axs[mod_item_index, rpm_index].bar_label(bar_plot, padding=3, fontsize=5)
            multiplier += 1
            green_color = green_color - 0.3

        # Add some text for labels, title and custom x-axis tick labels, etc.
        axs[mod_item_index, rpm_index].set_xlabel('Loss Types')
        axs[mod_item_index, rpm_index].set_ylabel('Losses (W)')
        axs[mod_item_index, rpm_index].set_title(f'Loss comparison at T = {torque_dict[rpm]} N.m & N = {rpm} rpm for {keyname}')
        axs[mod_item_index, rpm_index].set_xticks(x_bars + width*(num_bars-1)/2, loss_types)
        axs[mod_item_index, rpm_index].legend(loc='upper right', ncols=num_bars)
        axs[mod_item_index, rpm_index].set_ylim(0, ymax*1.25)
        axs[mod_item_index, rpm_index].grid(visible=True, which="major", axis='y')

fig.tight_layout()

plt.show()