#%% Load modules
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.tri as tri
from scipy.spatial import ConvexHull
import numpy as np
from datetime import datetime
import pandas as pd
import os

COLOR = 'black'

#%% Heatmap plot function
def show_heatmap(x, y, z, parameters):
    """
    Show the efficiency points and add a contour plot for efficiency values
    """
    # Create grid values first.
    xi, yi = np.linspace(x.min(), x.max(), 100), np.linspace(y.min(), y.max(), 100)

    # Linearly interpolate the data (x, y) on a grid defined by (xi, yi).
    triang = tri.Triangulation(x, y)
    interpolator = tri.LinearTriInterpolator(triang, z)
    Xi, Yi = np.meshgrid(xi, yi)
    zi = interpolator(Xi, Yi)
    fig, (ax1) = plt.subplots(nrows=1)
    
    # Creating outer plot
    points = np.column_stack((x, y))
    hull = ConvexHull(points)
    ax1.plot(points[hull.vertices,0], points[hull.vertices,1], color=COLOR, linestyle='dashed', lw=2)

    cntr1 = ax1.contourf(xi, yi, zi, levels=100, cmap="PiYG")

    fig.colorbar(cntr1, ax=ax1)
    ax1.plot(x, y, color=COLOR, linestyle='none', marker='o', ms=1)
    ax1.set(xlim=(0, x.max()), ylim=(0, y.max()))
    ax1.set_xlabel("Speed [RPM]")
    ax1.set_ylabel("Torque [N.m]")
    ax1.set_title("Inverter Losses [W]\nRg = {0:.0f} Ω, Fsw ={1:.0f} kHz, Vbus = {2:.0f} V, T_case = {3:.0f} °C".format(parameters['Rg'], parameters['switching_frequency']/1e3, parameters['bus_voltage'], parameters['case_temperature']))
    
    return fig


#%% Load data, parameters and plot heatmap
script_folder = os.path.realpath(os.path.dirname(__file__))
data = pd.read_pickle(os.path.join(script_folder, 'map_data_2024-05-02.pkl'))
parameters = pd.read_pickle(os.path.join(script_folder, 'map_parameters_2024-05-02.pkl'))
fig = show_heatmap(data['speed'], data['torque'], data['efficiency'], parameters)

plt.show()