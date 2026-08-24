""" Lithium-ion battery model
based on LIR18650 data from https://www.ineltro.ch/media/downloads/SAAItem/45/45958/36e3e7f3-2049-4adb-a2a7-79c654d92915.pdf"""
#
import numpy as np
from scipy.interpolate import interp1d, RegularGridInterpolator
import matplotlib.pyplot as plt

log = False


# Battery data

## Capacity: 2.6 Ah
Q = 2.6

## Maximum nominal resistance:
Rint_nom = 0.07

## Current rate dependance, at 25°C
data_0_2C_sod = sorted([0.0013054630696230048, 0.033942537812438535, 0.07441254037366403, 0.11749341927391171, 0.1657963496535474, 0.212793717363112, 0.2610965481422998, 0.30417752664299536, 0.35639684623150003, 0.41514358076856783, 0.476501241444882, 0.5456918797398298, 0.624020859122587, 0.6827675936596549, 0.7467362800756626, 0.8459529673737322, 0.7976501365945443, 0.8851174570651107, 0.9242819467564891, 0.9503916065507417, 0.9686682887263597, 0.983028681293557, 0.9934725850514368, 0.9999999999999999])
data_0_2C_volt = sorted([4.173875728274299, 4.108779448012498, 4.060813657759581, 4.012847998202926, 3.9717344823713203, 3.923768692118403, 3.8860813788455846, 3.855246209297814, 3.8244111704463073, 3.790149929036013, 3.7627408313507664, 3.7387580669205716, 3.7147751717941127, 3.7044968255102773, 3.6839400022463424, 3.6496787608360477, 3.670235584099983, 3.629122068268377, 3.605139173141918, 3.546895036605165, 3.447537514933069, 3.3310492418595627, 3.176873655513238, 3.00899352032429], reverse=True)

data_0_5C_sod = sorted([0, 0.07049605156434709, 0.026109659794252338, 0.11749341927391171, 0.16710181272317037, 0.2154046435023581, 0.25848562200305375, 0.30417752664299536, 0.35378592009225396, 0.4125326546293218, 0.47519577837525884, 0.5469973428094527, 0.6227153960529638, 0.6814621305900317, 0.7454308170060395, 0.8459529673737322, 0.7989555996641674, 0.8864230197351814, 0.9229763840864185, 0.9503916065507417, 0.9686682887263597, 0.9817231186234859, 0.990861658912191])
data_0_5C_volt = sorted([4.132762343138957, 4.047109239613221, 3.992291174938992, 3.94089931282355, 3.89635972512942, 3.8518201374352903, 3.814132693466208, 3.7832976546147012, 3.749036413204407, 3.7147751717941127, 3.6839400022463424, 3.6496787608360477, 3.635974342689688, 3.625695865709589, 3.6085652450044416, 3.564025657310312, 3.5914346242992945, 3.5331906184588053, 3.498929377048511, 3.4269806916691343, 3.324196967438251, 3.194004276218385, 3.005567448461766], reverse=True)

data_1C_sod = sorted([0.0013054630696230048, 0.03524805068228545, 0.07571800344328714, 0.11749341927391171, 0.16318532391385343, 0.211488254293489, 0.2610965481422998, 0.30548298971261845, 0.35639684623150003, 0.4112270919592509, 0.47127938916638956, 0.5378590017216436, 0.6201043703132698, 0.6840730567292778, 0.7441252543359688, 0.8472584304433552, 0.7976501365945443, 0.8851174570651107, 0.917754531807926, 0.9425586289321075, 0.9608355103086215, 0.9791121924842398])
data_1C_volt = sorted([4.04025696519191, 3.923768692118403, 3.8655245555816498, 3.8278372423088314, 3.7867237264772253, 3.7387580669205716, 3.707922897372801, 3.6770877278250307, 3.6428264864147364, 3.6154175194257534, 3.588008552436771, 3.560599585447788, 3.540042762183853, 3.519486069616182, 3.498929377048511, 3.4441113123742815, 3.4783725537845758, 3.4201284172478226, 3.372162757691169, 3.2933619285867444, 3.1837257992382857, 3.005567448461766], reverse=True)

data_2C_sod = sorted([0.0013054630696230048, 0.033942537812438535, 0.07310707730404094, 0.11488249313466561, 0.16318532391385343, 0.211488254293489, 0.2610965481422998, 0.30548298971261845, 0.3524803574221831, 0.4164490438381909, 0.47258485223601265, 0.5365535386520206, 0.6214099329833407, 0.6853785197989009, 0.7441252543359688, 0.8472584304433552, 0.7963445739244733, 0.8877283832043569, 0.9112271168593629, 0.9281984355658062, 0.9412532654629324])
data_2C_volt = sorted([3.899785796991944, 3.735331864361784, 3.6736616559625066, 3.625695865709589, 3.588008552436771, 3.560599585447788, 3.5331906184588053, 3.5023554489110347, 3.4783725537845758, 3.447537514933069, 3.4201284172478226, 3.3995717246801513, 3.372162757691169, 3.3447537907021863, 3.3173446930169392, 3.2385439946087793, 3.2899357260279567, 3.1905782043558615, 3.12890786526032, 3.070663859419831, 2.9987153047367183], reverse=True)

data_3C_sod = sorted([0.0026109759394700224, 0.01566580583659617, 0.0430809287004716, 0.07963449225260408, 0.1292427861014149, 0.18798952063848273, 0.24804171824517365, 0.30548298971261845, 0.34986943128293696, 0.41514358076856783, 0.481723193323822, 0.5535247577580158, 0.6174934441740237, 0.6814621305900317, 0.7428197912663457, 0.8211487706491026, 0.7924281847156043, 0.8459529673737322])
data_3C_volt = sorted([3.759314759488243, 3.622269793847065, 3.522912141478706, 3.4646681356382167, 3.4201284172478226, 3.3858671758375283, 3.3550321369860217, 3.3310492418595627, 3.310492549291892, 3.276231307881597, 3.245396138333827, 3.2179870406485804, 3.1871521324933374, 3.156316962945567, 3.115203316417697, 3.0432547617345844, 3.080942075007403, 3.0021413765992424], reverse=True)

## Temperature influence
data_0_5C_55deg_sod = [0, 0.09999998742407444, 0.20000001676790083, 0.29890111981490924, 0.3989011072389837, 0.504395600387892, 0.6043955878119665, 0.7054945434526106, 0.8021977939059832, 0.8725275677912605, 0.9153846453733613, 0.9472527115057939, 0.9648351968968653]
data_0_5C_55deg_volt = [4.020459303056453, 3.896450989884005, 3.8137787333191127, 3.734864391304769, 3.6747390486440366, 3.6334029920364816, 3.5883090208783783, 3.565762106974218, 3.5319415927681947, 3.4943633073614055, 3.4229645077485937, 3.2651358237199055, 2.994571996771285]

data_0_2C_minus20deg_sod = [0, 0.006593390101899792, 0.09010990227122476, 0.20000001676790083, 0.30000000419197526, 0.3999999916160497, 0.5032967160108259, 0.6021978190578343, 0.6912087950322413, 0.7483517048742151, 0.785714276731482]
data_0_2C_minus20deg_volt = [3.7649269909602436, 3.6747390486440366, 3.5469729642708234, 3.4079332795957473, 3.3440501657342496, 3.2914405088248317, 3.2425887664659623, 3.1862213383557787, 3.122338224494281, 3.0546974827818, 2.994571996771285]

# Dictionary mapping current rates to their SOD and voltage data
current_rate_data = {
    0.2: {'sod': data_0_2C_sod, 'volt': data_0_2C_volt},
    0.5: {'sod': data_0_5C_sod, 'volt': data_0_5C_volt},
    1.0: {'sod': data_1C_sod, 'volt': data_1C_volt},
    2.0: {'sod': data_2C_sod, 'volt': data_2C_volt},
    3.0: {'sod': data_3C_sod, 'volt': data_3C_volt},
}

current_rates = np.asarray(list(current_rate_data.keys()))

# Temperature data dictionary
temperature_data = {
    '0.5C_55deg': {'sod': data_0_5C_55deg_sod, 'volt': data_0_5C_55deg_volt},
    '0.2C_minus20deg': {'sod': data_0_2C_minus20deg_sod, 'volt': data_0_2C_minus20deg_volt},
}

def get_current_rate_data(rate):
    """ Returns the SOD and voltage data for a given current rate. """
    if rate in current_rate_data:
        return np.asarray(current_rate_data[rate]['sod']).flatten(), np.asarray(current_rate_data[rate]['volt']).flatten()
    else:
        raise ValueError(f"Current rate {rate}C not found in the data.")


def get_all_discharge_data_flattened():
    current_rate_flatten = []
    sod_flatten = []
    volt_flatten = []

    for rate, data in current_rate_data.items():
        current_rate_flatten.extend(np.full(len(data["sod"]), rate))
        sod_flatten.extend(data["sod"])
        volt_flatten.extend(data["volt"])
    return np.asarray(sod_flatten), np.asarray(current_rate_flatten), np.asarray(volt_flatten)


def plot_current_rate_data():
    """Plot the voltage vs SOD for different current rates."""
    plt.figure(figsize=(10, 6))
    colors = ['red', 'green', 'cyan', 'blue', 'magenta']
    markers = ['o', 's', '^', 'D', 'x']
    
    for i, rate in enumerate(current_rates):
        data = current_rate_data[rate]
        label = f"{rate}C"
        plt.plot(data['sod'], data['volt'], 
                 color=colors[i], marker=markers[i], linestyle='-', 
                 label=label, markersize=4, linewidth=1.5)
    
    plt.xlabel('State of Discharge (SOD)', fontsize=12)
    plt.ylabel('Voltage (V)', fontsize=12)
    plt.grid(which='both', linestyle='--', alpha=0.7)
    plt.legend(fontsize=10)
    plt.title('Voltage vs. SOD at Different Current Rates (25°C)', fontsize=14)
    plt.tight_layout()
    plt.show()


def plot_temperature_data():
    """Plot the voltage vs SOD for different temperatures."""
    plt.figure(figsize=(10, 6))
    
    # 0.5C at 55°C
    plt.plot(temperature_data['0.5C_55deg']['sod'], 
             temperature_data['0.5C_55deg']['volt'],
             'r-o', label='0.5C 55°C', markersize=4, linewidth=1.5)
    
    # 0.2C at -20°C
    plt.plot(temperature_data['0.2C_minus20deg']['sod'], 
             temperature_data['0.2C_minus20deg']['volt'],
             'g-o', label='0.2C -20°C', markersize=4, linewidth=1.5)
    
    plt.xlabel('State of Discharge (SOD)', fontsize=12)
    plt.ylabel('Voltage (V)', fontsize=12)
    plt.grid(which='both', linestyle='--', alpha=0.7)
    plt.legend(fontsize=10)
    plt.title('Voltage vs. SOD at Different Temperatures', fontsize=14)
    plt.tight_layout()
    plt.show()


INTERP_METHOD = 'quadratic'

def get_interpolator(rate):
    """Get interpolation function for a specific current rate.
    
    Args:
        rate (float): Current rate in C
        
    Returns:
        function: Interpolation function that maps SOD to voltage
    """
    data = current_rate_data[rate]
    return interp1d(data['sod'], data['volt'], kind=INTERP_METHOD, fill_value='extrapolate')


MESH_RESOLUTION = 100

def create_mesh():
    """Create mesh data for voltage vs SOD and current rate.
    
    Returns:
        tuple: (sod_array, mesh_voltage, mesh_sod, mesh_current_rate)
    """
    # Create interpolators for each current rate
    interpolators = {rate: get_interpolator(rate) for rate in current_rates}
    
    # Create SOD array
    sod = np.linspace(0, 1, MESH_RESOLUTION)
    
    # Create mesh grid
    mesh_sod, mesh_current_rate = np.meshgrid(sod, current_rates, indexing='ij')
    mesh_voltage = np.zeros(mesh_current_rate.shape)
    
    # Fill mesh voltage using vectorized approach
    for i, rate in enumerate(current_rates):
        mesh_voltage[:, i] = interpolators[rate](mesh_sod[:, i])
    
    return sod, mesh_voltage, mesh_sod, mesh_current_rate


def plot_ocv_internal_resistance():
    """Plot OCV, 3D voltage mesh, and internal resistance vs SOD."""
    sod, mesh_voltage, mesh_sod, mesh_current_rate = create_mesh()
    
    # Plot 3D mesh
    fig = plt.figure(figsize=(12, 5))
    
    # 3D plot
    ax1 = fig.add_subplot(121, projection='3d')
    ax1.plot_wireframe(mesh_sod, mesh_current_rate, mesh_voltage, 
                       color='black', alpha=0.5, linewidth=0.5)
    ax1.set_xlabel('SOD', fontsize=10)
    ax1.set_ylabel('Current rate (C)', fontsize=10)
    ax1.set_zlabel('Voltage (V)', fontsize=10)
    ax1.set_title('Voltage Surface', fontsize=12)
    
    # Compute OCV with 3D interpolation (at 0C rate)
    f = RegularGridInterpolator((sod, current_rates), mesh_voltage, 
                                method='slinear', bounds_error=False, fill_value=None)
    ocv = f((sod, 0))
    
    # Plot OCV vs SOD
    ax2 = fig.add_subplot(122)
    ax2.plot(sod, ocv, 'r-', label='OCV', linewidth=2)
    ax2.set_xlabel('SOD', fontsize=10)
    ax2.set_ylabel('OCV (V)', fontsize=10)
    ax2.grid(which='both', linestyle='--', alpha=0.7)
    ax2.set_title('Open Circuit Voltage vs. SOD', fontsize=12)
    ax2.legend(fontsize=10)
    
    plt.tight_layout()
    plt.show()
    
    # Compute and plot internal resistance vs SOD for different current rates
    plt.figure(figsize=(10, 6))
    
    # Create colormap for different rates
    colors = plt.cm.viridis(np.linspace(0, 1, len(current_rates)))
    
    Rint = np.zeros(mesh_voltage.shape)
    for i, rate in enumerate(current_rates):
        Rint[:, i] = (ocv - mesh_voltage[:, i]) / rate
        plt.plot(sod, Rint[:, i], color=colors[i], 
                 label=f'{rate}C', linewidth=2, marker='o', markersize=3)
    
    Rint_average = np.mean(Rint, axis=1)
    plt.plot(sod, Rint_average, 'k--', label='average', linewidth=2.5)
    
    plt.legend(fontsize=10)
    plt.grid(which='both', linestyle='--', alpha=0.7)
    plt.title(f'Internal Resistance vs. SOD (Nominal: {Rint_nom} Ohm)', fontsize=14)
    plt.xlabel('State of Discharge (SOD)', fontsize=12)
    plt.ylabel('Internal Resistance (Ohm)', fontsize=12)
    plt.tight_layout()
    plt.show()


if log:
    plot_current_rate_data()
    plot_temperature_data()
    plot_ocv_internal_resistance()