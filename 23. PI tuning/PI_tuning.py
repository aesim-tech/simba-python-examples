# Load modules
from aesim.simba import JsonProjectRepository
import matplotlib.pyplot as plt
import os
import numpy as np

# Load SIMBA project
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "DC-DC_Average-current_mode_control.jsimba")
project = JsonProjectRepository(file_path)
Average_Current_Mode_Control = project.GetDesignByName('Average Current Mode Control')


# PI definition 
kp_c = np.arange(1, 7, 1).tolist()   # Kp values 
ki_c = np.arange (1000, 100000, 20000).tolist()  # Ki values
Vouts = []

# plot file creation + sweep of PI

numrows = 2     # line definition
numcols = (int(len(kp_c)-numrows)-1)    # column definition

fig = plt.figure(figsize = (16, 9))
fig.suptitle("Output voltage = VR1")
count = 0
 
for kp in kp_c:   # Kp loop
    
    # Set Kp value
    PID1= Average_Current_Mode_Control.Circuit.GetDeviceByName('PID1')
    PID1.Kp=kp
    
    # Run calculation
    job = Average_Current_Mode_Control.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != 'OK':
        print(job.Summary())
    
    axis_indice = f"{numrows}{numcols}{count+1}"   # axis definition
    ax1 = fig.add_subplot(numrows, numcols, count+1)

    for ki in ki_c:  # Ki loop
        # Set Ki value
        PID1= Average_Current_Mode_Control.Circuit.GetDeviceByName('PID1')
        PID1.Ki=ki
    
        # Run calculation
        job = Average_Current_Mode_Control.TransientAnalysis.NewJob()
        status = job.Run()
        if str(status) != 'OK':
            print(job.Summary())
    
        # Retrieve results
        Vout_signal = job.GetSignalByName('R1 - Instantaneous Voltage')
        t = np.array(Vout_signal.TimePoints)
        Vout = np.array(Vout_signal.DataPoints)

        ax1.plot(t,Vout, label= 'ki = ' + str("{:.1e}".format(ki)))
        ax1.legend(fontsize=8) 

    ax1.set_title(f'Kp: {np.round(kp, 2)}')
    ax1.label_outer()
    count += 1
    
fig.tight_layout()
plt.show()
