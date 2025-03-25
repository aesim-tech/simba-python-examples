"""
Python notebook / script to compute magnetic losses of the transformer and powerswitch losses in a Dual Active Bridge (DAB) converter
"""
#%%
import os
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from aesim.simba import ProjectRepository

#%% #########
# PRE-PROCESS
#############

print("Loss data for DMR44 and define magnetic loss function")

## Data for 100 kHz and 25°C
data_100k_25C_x = [50.43988739093397, 81.06823664212065, 153.55415016812432, 296.20911241965206]
data_100k_25C_y = [26.941434246171102, 79.9673347137438, 329.4574652351894, 1440.70827878885]

## Data for 100 kHz and 100°C
data_100k_100C_x = [50.74767107013431, 93.24314401826693, 161.21209514454034, 296.20911241965206]
data_100k_100C_y = [6.3472995818200415, 33.19216637405551, 161.78532101352494, 840.0301178252122]

## Data for 200 kHz and 25°C
data_200k_25C_x = [50.74767107013431, 89.90107011797573, 166.19106151917026, 298.0165774071646]
data_200k_25C_y = [72.04522101505854, 271.429444531243, 1069.3656104673032, 3969.2230216707258]

## Data for 200 kHz and 100°C
data_200k_100C_x = [49.52769134960666, 96.70945957597505, 174.47922568335946, 262.2758216661127]
data_200k_100C_y = [27.345961868755982, 140.88582968667282, 625.3404255629255, 1748.7126295116889]

# Define Magnetic loss function
def compute_loss_density(flux_density: float, frequency: float, temperature: float):
    """ compute loss density for a given flux density, frequency and temperature """
    if flux_density <= 0 or frequency <= 0 or temperature < 0:
        return 0
    else:
        # Create interpolators for each dataset
        interp_100k_25C = interp1d(np.log10(data_100k_25C_x), np.log10(data_100k_25C_y), kind='linear', fill_value='extrapolate')
        interp_100k_100C = interp1d(np.log10(data_100k_100C_x), np.log10(data_100k_100C_y), kind='linear', fill_value='extrapolate')
        interp_200k_25C = interp1d(np.log10(data_200k_25C_x), np.log10(data_200k_25C_y), kind='linear', fill_value='extrapolate')
        interp_200k_100C = interp1d(np.log10(data_200k_100C_x), np.log10(data_200k_100C_y), kind='linear', fill_value='extrapolate')
    
        # Compute losses for the given flux density from each interpolator
        y_100k_25C = interp_100k_25C(np.log10(flux_density))
        y_100k_100C = interp_100k_100C(np.log10(flux_density))
        y_200k_25C = interp_200k_25C(np.log10(flux_density))
        y_200k_100C = interp_200k_100C(np.log10(flux_density))
    
        # Interpolate over temperature for each frequency
        temperatures = [25, 100]
        y_100k_T = np.interp(temperature, temperatures, [y_100k_25C, y_100k_100C])
        y_200k_T = np.interp(temperature, temperatures, [y_200k_25C, y_200k_100C])
    
        # Interpolate over frequency
        frequencies = [100e3, 200e3]  # Frequencies in Hz
        interp_loss_density = 10**(np.interp(np.log10(frequency), np.log10(frequencies), [y_100k_T, y_200k_T]))
        
        return max(interp_loss_density, 0)

def plot_magnetic_loss_data():
    """ plot the magnetic loss data """
    plt.figure()
    plt.loglog(data_100k_25C_x, data_100k_25C_y, 'r', label = '100kHz, 25°C')
    plt.loglog(data_100k_100C_x, data_100k_100C_y, 'r--', label = '100kHz, 100°C')
    plt.loglog(data_200k_25C_x, data_200k_25C_y, 'b', label = '200kHz, 25°C')
    plt.loglog(data_200k_100C_x, data_200k_100C_y, 'b--', label = '200kHz, 100°C')
    plt.xlabel('Flux density (mT)')
    plt.ylabel('Loss density (mW / cm3)')
    plt.xlim(10, 1000)
    plt.ylim(1, 1e4)
    plt.grid(which='both')
    plt.legend()
    plt.show()

flux_density = 200  # flux_density 200 mT
frequency = 100e3  # Frequency 150 kHz
temperature = 100  # Temperature 60°C
print(f"The interpolated loss density at:\n - B = {flux_density} mT,\n - frequency = {frequency/1e3:0.0f} kHz,\n - temperature = {temperature}°C,\nis {compute_loss_density(flux_density, frequency, temperature):0.0f} mW / cm3\n")

flux_density = 0  # flux_density 100 mT
frequency = 300e3  # Frequency 150 kHz
temperature = 60  # Temperature 60°C
print(f"The interpolated loss density at:\n - B = {flux_density} mT,\n - frequency = {frequency/1e3:0.0f} kHz,\n - temperature = {temperature}°C,\nis {compute_loss_density(flux_density, frequency, temperature):0.0f} mW / cm3")

plot_magnetic_loss_data()


print("Simulation methods and Signal Computation")

def run_simulation(Vin, fsw, phase_shift, Lm, Rlk, Rpri, Rsec):
    # For unit tests only
    if os.environ.get("SIMBA_SCRIPT_TEST"):
        endtime = 10 / fsw
        print("Running in test mode")
    else:
        endtime = 0.6
    
    # Load the project
    script_folder = os.path.realpath(os.path.dirname(__file__))
    project = ProjectRepository(os.path.join(script_folder, 'dual_active_bridge_ti.jsimba'))

    # From the electrical model of the transformer
    design = project.GetDesignByName('1- ElectroThermal Model - OpenLoop')
    design.TransientAnalysis.CompressScopes = True
    design.TransientAnalysis.TimeStep = 2e-9
    design.TransientAnalysis.EndTime = endtime
    design.TransientAnalysis.DualStageElectroThermalAnalysis = True
    design.Circuit.GetDeviceByName('Vin').Value = Vin
    design.Circuit.GetDeviceByName('Lm').Value = float(np.format_float_scientific(Lm, precision=3))
    design.Circuit.GetDeviceByName('Rlk').Value = Rlk
    design.Circuit.GetDeviceByName('Rpri').Value = Rpri
    design.Circuit.GetDeviceByName('Rsec').Value = Rsec
    design.Circuit.GetDeviceByName('PhaseShift').Value = phase_shift
    design.Circuit.SetVariableValue('fsw', str(fsw))
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    if str(status) != "OK": 
        raise Exception(job.Summary())

    # Get electrical waveforms, powerswitch loss
    results = {'iLm': job.GetSignalByName('Lm - Current'),
                         'iPri': job.GetSignalByName('Llk - Current'),
                         'iSec': job.GetSignalByName('Rsec - Current'),
                         'Tj_T1': job.GetSignalByName('T1 - Junction Temperature (°)'),
                         'Tj_D1': job.GetSignalByName('D1 - Junction Temperature (°)'),
                         'Tj_T5': job.GetSignalByName('T5 - Junction Temperature (°)'),
                         'Tj_D5': job.GetSignalByName('D5 - Junction Temperature (°)'),
                         'switch_loss': job.GetSignalByName('Heat Flow - Heat Flow')}
  
    return results
    #timestamp = datetime.now().strftime("%Y-%m-%d")
    #data.to_pickle(os.path.join(script_folder, "results_" + timestamp + ".pkl"))

def run_mag_model_simulation(fsw, phase_shift):
    """ run simulation with magnetic model of the transformer and returns the flux signal"""
    script_folder = os.path.realpath(os.path.dirname(__file__))
    project = ProjectRepository(os.path.join(script_folder, 'dual_active_bridge_ti.jsimba'))
    design_mag = project.GetDesignByName('2- ElectroMagnetoThermal Model - OpenLoop')
    design_mag.TransientAnalysis.CompressScopes = True
    design_mag.TransientAnalysis.TimeStep = 2e-9
    design_mag.TransientAnalysis.EndTime = 0.5
    design_mag.Circuit.GetDeviceByName('PhaseShift').Value = phase_shift
    design_mag.Circuit.SetVariableValue('fsw', str(fsw))
    job_mag = design_mag.TransientAnalysis.NewJob()
    if str(job_mag.Run()) != "OK": 
        raise Exception(job_mag.Summary())
    return job_mag.GetSignalByName('flux - Out')

def steadystate_signal(horizon_time: float, *signals):
    timepoints_list = []
    for signal in signals:
        timepoints_list.extend(signal.TimePoints)
    timepoints = sorted(timepoints_list)
    steadystate_maskarray = np.array(timepoints) > (timepoints[-1] - horizon_time)
    steadystate_time = np.array(timepoints)[steadystate_maskarray]
    steadystate_datapoints_list = [np.interp(steadystate_time, signal.TimePoints, signal.DataPoints) for signal in signals]
    return steadystate_time, *steadystate_datapoints_list

def compute_fft(time, signal, fstep):
    N = 10000
    time_resamp = np.linspace(time[0], time[-1], N, endpoint=False)
    signal_resamp = np.interp(time_resamp, time, signal)
    freqs = np.fft.rfftfreq(N) * fstep * len(signal_resamp)
    fft = np.abs(np.fft.rfft(signal_resamp) / len(signal_resamp))
    fft[1:] = 2 * fft[1:]
    return freqs, fft

def compute_rms(time, data):
    """ compute rms value of a given signal in steady state """
    dt = np.diff(time)
    squared_data = data[:-1] ** 2
    rms_value = np.sqrt(np.sum(squared_data * dt) / np.sum(dt))
    return rms_value


print("Loss Computation Methods")

# compute dc copper losses of inductor, primary and secondary windings
def compute_dc_copper_losses(time, iPri, iSec, Rpri, Rsec, Rlk):   
    iPri_rms = compute_rms(time, iPri)
    iSec_rms = compute_rms(time, iSec)

    dcLoss_inductor = iPri_rms ** 2 * Rlk
    dcLoss_pri = iPri_rms ** 2 * Rpri
    dcLoss_sec = iSec_rms ** 2 * Rsec

    print(f"Primary RMS current: {iPri_rms:.2f} A")
    print(f"Secondary RMS current: {iSec_rms:.2f} A")
    print(f"Inductor DC loss: {dcLoss_inductor:.2f} W")
    print(f"Primary DC loss: {dcLoss_pri:.2f} W")
    print(f"Secondary DC loss: {dcLoss_sec:.2f} W")

    return dcLoss_inductor, dcLoss_pri, dcLoss_sec

# compute flux density and its FFT
def compute_flux_density(time: np.ndarray, iLm: np.ndarray, Lm: float, Npri: float, Ac: float, fsw: float):
    flux_density_estimated = Lm * iLm / Npri / Ac
    freqs, fft_flux_densities_estimated = compute_fft(time, flux_density_estimated, fsw)
    max_index = 10
    freqs = freqs[:max_index]
    fft_flux_densities_estimated = fft_flux_densities_estimated[:max_index]
    
    plt.figure()
    plt.subplot(2, 1, 1)
    plt.plot(time, flux_density_estimated, color='blue', linestyle='-', linewidth=1.5, label='Signal')
    plt.title('Flux density (B)')
    plt.xlabel('Time [s]')
    plt.grid(True)

    plt.subplot(2, 1, 2)
    plt.stem(freqs, fft_flux_densities_estimated)
    plt.title('FFT Flux density estimated')
    plt.xlabel('Frequency [Hz]')
    plt.grid(True)

    plt.tight_layout()
    plt.show()

    return flux_density_estimated, freqs, fft_flux_densities_estimated

# Compute Core Loss with fft of flux density
def compute_magnetic_losses_fftmethod(freqs, fft_flux_densities, temperature, core_volume):
    total_loss_density = 0
    print(f"\n--- Core Loss computation with FFT of flux density method ---")
    for freq, fft_flux_density in zip(freqs, fft_flux_densities):
        total_loss_density += compute_loss_density(fft_flux_density*1e3, freq, temperature)
        if fft_flux_density * 1e3 >= 1:
            print(f"Loss density at {temperature}°C, {freq/1e3:0.0f} kHz, {fft_flux_density*1e3:0.0f} mT is {compute_loss_density(fft_flux_density*1e3, freq, temperature):0.2f} mW / cm3")
    print(f"Total Loss density at {temperature}°C: {total_loss_density : 0.1f} mW / cm3")
    print(f"Total Core Loss (FFT) at {temperature}°C: {total_loss_density * core_volume / 1e6 : 0.1f} W")
    return total_loss_density * core_volume / 1e6

# Compute Core Loss with max flux density
def compute_magnetic_losses_maxmethod(flux_density, fft_flux_densities, temperature, Ac, fsw, core_volume):
    # Compute core loss from maximum flux density
    print(f"\n--- Core Loss computation with max flux density method ---")
    flux_density_max = np.max(flux_density) - fft_flux_densities[0]
    print(f"Estimated maximum flux density: {flux_density_max*1e3:.0f} mT")
    print(f'Theoretical maximum flux density: {500 / 15 / Ac / 4 / fsw*1e3:.0f} mT (for comparison)')
    core_Loss = compute_loss_density(flux_density_max*1e3, fsw, temperature) * core_volume / 1e6
    print(f"Total Core Loss (max flux density) at {temperature}°C : {core_Loss: 0.1f} W")
    return core_Loss

# Compute efficiency and Loss coefficient
def compute_efficiency(core_Loss, dcLoss_inductor, dcLoss_pri, dcLoss_sec, powerswitch_loss):
    efficiency = 1e4 / (1e4 + core_Loss + dcLoss_inductor + dcLoss_pri + dcLoss_sec + powerswitch_loss)
    print(f"Efficiency: {efficiency * 100:.2f}%")
    loss_coeff = 1 - efficiency
    print(f"Loss coefficient: {loss_coeff * 100:.2f}%")

#%%##########
# SIMULATION
#############

# Compute transformer volume based on 2 E-core E64/18/50
A = 64                          # width of the core (mm)
B = 18                          # height of the core (mm)
C = 50                          # thickness of the core (mm)
base = A * B / 2 * C            # volume of the base of the e-core (mm3)
legs = 2 * (B * C * B / 2)      # 1 central leg + 2 side legs = 2 central legs
single_ecore_volume = base + legs
core_volume = 2 * single_ecore_volume
print(f'Core volume: {core_volume / 1e3 :0.1f} cm3')

# Compute equivalent magnetizing inductor
Ac = 0.000516                   # core section m²
Le = 0.112                      # magnetic path length (m)
ur = [2400, 2200]               # relative permeability µi and µe (SI)
Npri = 24
uo = 4 * np.pi * 1e-7
R = Le / Ac / (uo * np.array(ur))
Lm = Npri**2 / R
print(f'Magnetizing inductor: {Lm[0] * 1e3:.2f} mH for µe = µi = {ur[0]}')
print(f'Magnetizing inductor: {Lm[1] * 1e3:.2f} mH for µe = {ur[1]}')

# Simulate 
Vin = 800
fsw = 100e3
phase_shift = 23
Rlk = 23e-3
Rpri = 43e-3
Rsec = 16e-3
res = run_simulation(Vin, fsw, phase_shift, Lm[0], Rlk, Rpri, Rsec)

#%%###########
# POST-PROCESS
##############

# Powerswitch losses and junction temperatures
plt.figure()
for signal in [res['Tj_T1'], res['Tj_D1'], res['Tj_T5'], res['Tj_D5']]:
    plt.plot(signal.TimePoints, signal.DataPoints, label=signal.Name)
plt.xlabel('Time (s)')
plt.ylabel('Junction Temperature (°C)')
plt.legend(loc='upper left')
plt.grid(True)
plt.show()
powerswitch_loss = res['switch_loss'].DataPoints[-1]
print(f"Total Powerswitch Loss: {powerswitch_loss:.2f} W\n")

# DC Copper Losses
time, iPri, iSec, iLm = steadystate_signal(1 / fsw, res['iPri'], res['iSec'], res['iLm'])
dcLoss_inductor, dcLoss_pri, dcLoss_sec = compute_dc_copper_losses(time, iPri, iSec, Rpri, Rsec, Rlk)

# Core Magnetic Losses
flux_density, freqs, fft_flux_densities = compute_flux_density(time, iLm, Lm[0], Npri, Ac, fsw)
temperature = 100
core_Loss1 = compute_magnetic_losses_fftmethod(freqs, fft_flux_densities, temperature, core_volume)
core_Loss2 = compute_magnetic_losses_maxmethod(flux_density, fft_flux_densities, temperature, Ac, fsw, core_volume)

# Efficiency and Loss coefficient
compute_efficiency(core_Loss2, dcLoss_inductor, dcLoss_pri, dcLoss_sec, powerswitch_loss)