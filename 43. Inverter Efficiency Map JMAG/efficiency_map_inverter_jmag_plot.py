import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as tri
from datetime import datetime
from scipy.spatial import ConvexHull, Delaunay
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as tri
from scipy.spatial import ConvexHull

def show_heatmap(fig, ax1, x, y, z, xlabel, ylabel, title, cmap):
    """
    Display a heatmap with tricontourf to fill the entire area defined by the data points.
    """
    # Ensure inputs are numpy arrays
    x = np.asarray(x)
    y = np.asarray(y)
    z = np.asarray(z)
    
    # Remove NaNs and Infs from data
    valid_mask = (~np.isnan(x) & ~np.isnan(y) & ~np.isnan(z) &
                  ~np.isinf(x) & ~np.isinf(y) & ~np.isinf(z))
    x_clean, y_clean, z_clean = x[valid_mask], y[valid_mask], z[valid_mask]
    
    # Remove duplicate points
    points = np.column_stack((x_clean, y_clean))
    unique_points, unique_indices = np.unique(points, axis=0, return_index=True)
    x_unique = unique_points[:, 0]
    y_unique = unique_points[:, 1]
    z_unique = z_clean[unique_indices]
    
    # Check if there are enough points for triangulation
    if len(x_unique) < 3:
        print("Not enough unique points to perform triangulation.")
        return
    
    # Create triangulation
    triang = tri.Triangulation(x_unique, y_unique)
    
    # Plot Convex Hull if possible
    try:
        hull = ConvexHull(points)
        # Close the convex hull path by appending the first vertex index
        hull_vertices = np.append(hull.vertices, hull.vertices[0])
        ax1.plot(points[hull_vertices, 0], points[hull_vertices, 1], 'k--', lw=1)
    except Exception as e:
        print(f"An error occurred during ConvexHull calculation: {e}")
    
    # Create tricontourf plot
    cntr1 = ax1.tricontourf(triang, z_unique, levels=100, cmap=cmap)
    
    # Add colorbar
    fig.colorbar(cntr1, ax=ax1)
    
    # Plot original data points
    ax1.plot(x_unique, y_unique, 'ko', ms=1)
    
    zoom_out = 0.1
    # Calculate axis limits and zoom out
    x_min, x_max = x_unique.min(), x_unique.max()
    y_min, y_max = y_unique.min(), y_unique.max()
    x_range = x_max - x_min
    y_range = y_max - y_min

    # Adjust the limits to zoom out
    x_buffer = x_range * zoom_out
    y_buffer = y_range * zoom_out

    ax1.set_xlim(x_min - x_buffer, x_max + x_buffer)
    ax1.set_ylim(y_min - y_buffer, y_max + y_buffer)
    
    # Set labels and title
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