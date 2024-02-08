import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as tri
from scipy.spatial import ConvexHull, Delaunay
from datetime import datetime

def show_heatmap(fig, ax1, x, y, z, xlabel, ylabel, title, cmap):
    """
    Show the efficiency points and add a contour plot for efficiency values
    """
    # Create grid values first.
    xi, yi = np.linspace(x.min(), x.max(), 100), np.linspace(y.min(), y.max(), 100)
    
    scipy_triang = Delaunay(np.vstack((x, y)).T)
    triang = tri.Triangulation(x, y, triangles=scipy_triang.simplices)
   
    interpolator = tri.LinearTriInterpolator(triang, z)
    Xi, Yi = np.meshgrid(xi, yi)
    zi = interpolator(Xi, Yi)
    
    # Creating outer plot
    points = np.column_stack((x, y))
    hull = ConvexHull(points)
    ax1.plot(points[hull.vertices,0], points[hull.vertices,1], 'k--', lw=2)

    cntr1 = ax1.contourf(xi, yi, zi, levels=100, cmap=cmap)

    fig.colorbar(cntr1, ax=ax1)
    ax1.plot(x, y, 'ko', ms=1)
    ax1.set(xlim=(0, x.max()), ylim=(0, y.max()))
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel)
    ax1.set_title(title)

if os.environ.get("SIMBA_SCRIPT_TEST"):
    exit()

current_folder = os.path.dirname(os.path.abspath(__file__))
inverter_losses = np.loadtxt(os.path.join(current_folder, "results/inverter_losses.txt"))
motor_losses = np.loadtxt(os.path.join(current_folder,"results/motor_losses.txt"))
t = np.loadtxt(os.path.join(current_folder,"results/torque.txt"))
s = np.loadtxt(os.path.join(current_folder,"results/speed.txt"))
e = np.loadtxt(os.path.join(current_folder,"results/efficiency.txt"))*100

input_power = np.loadtxt(os.path.join(current_folder,"results/input_power.txt"))
efficiency_inverter = (1 - inverter_losses / (inverter_losses + input_power))*100

Pout = np.loadtxt(os.path.join(current_folder,"results/Pout.txt"))
efficiency_motor = (Pout / (Pout + motor_losses))*100

# Plot
fig, axs = plt.subplots(3, 2, figsize = (16, 9))
show_heatmap(fig, axs[0, 0], s, t, e, "Speed [RPM]", "Torque [N.m]", "Drive Efficiency (inverter + motor) [%]", "RdYlGn")
show_heatmap(fig, axs[0, 1], s, t, (inverter_losses + motor_losses), "Speed [RPM]", "Torque [N.m]", "Drive Losses (inverter + motor) [W]", "coolwarm")
show_heatmap(fig, axs[1, 0], s, t, inverter_losses, "Speed [RPM]", "Torque [N.m]", "Inverter Losses [W]", "coolwarm")
show_heatmap(fig, axs[1, 1], s, t, motor_losses, "Speed [RPM]", "Torque [N.m]", "Motor Losses [W]", "coolwarm")
show_heatmap(fig, axs[2, 0], s, t, efficiency_inverter, "Speed [RPM]", "Torque [N.m]", "Inverter Efficiency [%]", "RdYlGn")
show_heatmap(fig, axs[2, 1], s, t, efficiency_motor, "Speed [RPM]", "Torque [N.m]", "Motor Efficiency [%]", "RdYlGn")
fig.tight_layout(pad = 2)
path = "efficiency_map"+datetime.now().strftime("%m%d%Y%H%M%S")+".png"
fig.savefig(os.path.join(current_folder, path))
plt.show()