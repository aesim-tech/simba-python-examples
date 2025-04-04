# This script reads the 'loss_data.txt' file generated by the previous simulation script.
# It parses the switching and conduction losses data, constructs ThermalData objects,
# and applies them to SIMBA simulation projects for further analysis.

#%% Import Necessary Modules
import os
import ast  # For safe evaluation of string literals
import pandas as pd
from aesim.simba import ProjectRepository, ThermalData, IV_T, EI_VT

#%% Define File Paths
script_directory = os.path.realpath(os.path.dirname(__file__))
project_file_path = os.path.join(script_directory, "zvs_characterization_simulation_model.jsimba")
loss_data_file_path = os.path.join(script_directory, "loss_data.txt")

#%% Initialize Data Structures to Store Loss Data
switching_losses_data = {}    # Key: (Temperature, Voltage), Value: list of [Current, Energy Loss]
conduction_losses_data = {}   # Key: Temperature, Value: list of [Current, Conduction Loss]

# Variable to keep track of the current section in the results file
current_section = None

#%% Read and Parse the Results File
# Check if the results file exists
if not os.path.exists(loss_data_file_path):
    raise FileNotFoundError(f"Results file '{loss_data_file_path}' not found")

# Open the results file and parse its content
with open(loss_data_file_path, 'r') as file:
    for line in file:
        line = line.strip()  # Remove leading and trailing whitespace

        # Check for section headers
        if line == 'Switching Losses:':
            current_section = 'switching_losses'
            continue
        elif line == 'Conduction Losses:':
            current_section = 'conduction_losses'
            continue

        # Skip empty lines or header lines
        if not line or line.startswith('Temperature'):
            continue

        # Parse data lines based on the current section
        if current_section == 'switching_losses':
            # Expected format: Temperature (°C), Switched Current (A), Maximum Voltage (V), Switching Loss (J)
            try:
                temp_str, current_str, voltage_str, loss_str = line.split(', ')
                temperature = int(float(temp_str))
                current = float(current_str)
                voltage = float(voltage_str)
                energy_loss = float(loss_str)

                # In the original code, voltage is set to 800V (adjust if necessary)
                voltage = 800.0

                # Use (Temperature, Voltage) as the key for switching losses data
                key = (temperature, voltage)

                # Append the data to the dictionary
                if key not in switching_losses_data:
                    switching_losses_data[key] = []
                switching_losses_data[key].append([current, energy_loss])
            except ValueError as e:
                print(f"Error parsing line in switching losses: '{line}'. Error: {e}")
                continue

        elif current_section == 'conduction_losses':
            # Expected format: Temperature (°C), Forward Current (A), Reverse Current (A), Maximum Voltage (V), Delta Voltage (V), Conduction Loss (J)
            try:
                # Adjusted to unpack 6 values
                temp_str, fwd_current_str, rev_current_str, max_voltage_str, delta_voltage_str, conduction_loss_str = line.split(', ')
                temperature = int(float(temp_str))

                # Forward and reverse currents might be lists (e.g., '[value]')
                # Use ast.literal_eval to safely parse the strings into Python lists or values
                fwd_current_parsed = ast.literal_eval(fwd_current_str)
                rev_current_parsed = ast.literal_eval(rev_current_str)

                # Extract the first value if they are lists
                forward_current = fwd_current_parsed[0] if isinstance(fwd_current_parsed, list) else fwd_current_parsed
                reverse_current = rev_current_parsed[0] if isinstance(rev_current_parsed, list) else rev_current_parsed

                max_voltage = float(max_voltage_str)
                delta_voltage = float(delta_voltage_str)
                conduction_loss = float(conduction_loss_str)

                # Append the data to the dictionary
                if temperature not in conduction_losses_data:
                    conduction_losses_data[temperature] = []
                # We need to store [Current, Conduction Loss]
                conduction_losses_data[temperature].append([forward_current, conduction_loss])
            except Exception as e:
                print(f"Error parsing line in conduction losses: '{line}'. Error: {e}")
                continue

#%% Convert Data Dictionaries to Arrays for Processing
# Convert conduction losses data to arrays
for temperature in conduction_losses_data:
    conduction_losses_data[temperature] = pd.DataFrame(
        conduction_losses_data[temperature],
        columns=["Current (A)", "Conduction Loss (J)"]
    ).values

# Convert switching losses data to arrays
for key in switching_losses_data:
    switching_losses_data[key] = pd.DataFrame(
        switching_losses_data[key],
        columns=["Current (A)", "Energy Loss (J)"]
    ).values

#%% Define a Helper Function to Serialize Arrays into Strings
def array_to_string(array):
    """
    Convert a 2D array into a string formatted as '[x1 y1; x2 y2; ...]'.

    Parameters:
    - array: 2D numpy array or list of lists

    Returns:
    - A string representation of the array suitable for SIMBA ThermalData
    """
    # Start with an opening bracket
    result = "["

    # Loop through each pair in the array
    for i, (x_value, y_value) in enumerate(array):
        # Format each pair as 'x y'
        result += f"{x_value} {y_value}"
        if i < len(array) - 1:
            result += "; "  # Add a semicolon separator except after the last pair

    # Close the bracket
    result += "]"

    return result

#%% Create a ThermalData Object and Populate It with the Parsed Data
# Create a new ThermalData object for the device
thermal_data = ThermalData()
thermal_data.Name = "Infineon IMBG120R008M2H"

# Add conduction losses data
for temperature in conduction_losses_data:
    conduction_loss = IV_T()
    conduction_loss.Temperature = temperature
    # Serialize the array into a string
    conduction_loss.IVSerialized = array_to_string(conduction_losses_data[temperature])
    # Add the conduction loss data to the ThermalData object
    thermal_data.ConductionLosses.Add(conduction_loss)

# Add switching (turn-off) losses data
for key in switching_losses_data:
    switching_loss = EI_VT()
    temperature, voltage = key
    switching_loss.Temperature = temperature
    switching_loss.Voltage = voltage
    # Serialize the array into a string
    switching_loss.EISerialized = array_to_string(switching_losses_data[key])
    # Add the switching loss data to the ThermalData object
    thermal_data.TurnOffLosses.Add(switching_loss)

# Note: In this script, we are only adding Turn-Off losses.
# If Turn-On losses or other types of losses are available, they can be added similarly.

#%% Add Thermal Data to the SIMBA Project
# Load the SIMBA project file
zvs_project_file = os.path.join(script_directory, "zvs_characterization_infineonIMBG120R008M2H.jsimba")
zvs_project = ProjectRepository(zvs_project_file)

# Add the new ThermalData object to the project
zvs_project.AddThermalData(thermal_data)
zvs_project.Save()

#%% Apply Thermal Data to Another Project (e.g., LLC Full Bridge)
# Load the LLC project
llc_project_file = os.path.join(script_directory, "LLC_full_bridge.jsimba")
llc_project = ProjectRepository(llc_project_file)

# Retrieve existing thermal data (if any)
original_thermal_data = llc_project.GetThermalDataByName('Infineon IMBG120R008M2H (MOSFET with Diode)')
zvs_thermal_data = llc_project.GetThermalDataByName('Infineon IMBG120R008M2H (MOSFET with Diode) - ZVS')

# Clear existing data from the ZVS thermal data object
zvs_thermal_data.TurnOnLosses.Clear()
zvs_thermal_data.CustomVariables.Clear()
zvs_thermal_data.Constants.Clear()
zvs_thermal_data.Comment = "Custom Thermal Data Generated by SIMBA for ZVS"

# Assign the new Turn-Off and Conduction losses data
zvs_thermal_data.TurnOffLosses = thermal_data.TurnOffLosses
zvs_thermal_data.ConductionLosses = thermal_data.ConductionLosses

# Save the updated LLC project
llc_project.Save()

#%% Explanation of How Switching and Conduction Losses Are Applied
"""
In this script, we read the switching and conduction losses data generated from previous simulations.
The data is stored in the 'results.txt' file and includes losses calculated at different temperatures and currents.

- **Switching Losses:**
  - The switching losses are represented as energy losses (in joules) for specific currents and temperatures.
  - We create EI_VT (Energy vs. Current at specific Voltages and Temperatures) objects to store this data.
  - The switching losses are added to the ThermalData object under 'TurnOffLosses', as they are assumed to occur during turn-off events.

- **Conduction Losses:**
  - The conduction losses are represented as energy losses (in joules) for specific currents and temperatures.
  - We create IV_T (Current vs. Voltage at specific Temperatures) objects to store this data.
  - The conduction losses are added to the ThermalData object under 'ConductionLosses'.

By adding the ThermalData object to the SIMBA projects, we enable the simulation models to use this custom loss data.
This allows for more accurate thermal and efficiency analyses under various operating conditions.
"""