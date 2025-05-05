#!/usr/bin/env python3
"""
three_phase_inverter_simulation.py

This script builds a 3-phase inverter circuit in SIMBA, runs a transient simulation,
and plots the phase A output voltage and DC bus input current.
"""

from aesim.simba import Design
import matplotlib.pyplot as plt

# Create a new design
design = Design()
design.Name = "Three-phase Inverter Simulation"

# Configure transient analysis
ta = design.TransientAnalysis
ta.TimeStep = 1e-6    # 1 microsecond time step
ta.EndTime = 20e-3    # 20 ms (one cycle at 50 Hz)

circuit = design.Circuit

# Add DC voltage source for DC bus
vdc = circuit.AddDevice("DC Voltage Source", 0, 0)
vdc.Name = "Vdc"
vdc.Voltage = 400    # 400 V DC bus

# Add ground
gnd = circuit.AddDevice("Ground", 10, 0)

# Connect negative terminal of Vdc to ground
circuit.AddConnection(vdc.N, gnd.Pin)

# Define modulation parameters
fundamental_freq = 50    # 50 Hz output frequency
modulation_index = 0.8   # modulation index (0 to 1)

# Create three phase legs
for phase, offset in zip(['A', 'B', 'C'], [0, 1, 2]):
    # PWM signal generator
    pwm = circuit.AddDevice("Square Wave", 10, 10+offset * 3)
    pwm.Frequency = fundamental_freq
    pwm.Amplitude = modulation_index
    pwm.DutyCycle = 0.5

    # Upper and lower controlled switches
    sw_high = circuit.AddDevice("Controlled Switch", 20, offset * 3)
    sw_low  = circuit.AddDevice("Controlled Switch", 20, offset * 3 + 1)

    # Connect switches to DC bus and ground
    circuit.AddConnection(vdc.P, sw_high.P)
    circuit.AddConnection(vdc.N, sw_low.N)

    # Connect PWM to switches
    circuit.AddConnection(pwm.Out, sw_high.In)
    circuit.AddConnection(pwm.Out, sw_low.In)

    # Node between switches -> output phase node
    circuit.AddConnection(sw_high.N, sw_low.P)

    # Add series inductor for filtering
    L = circuit.AddDevice("Inductor", 30, offset * 3)
    L.Name = f"L_{phase}"
    circuit.AddConnection(sw_high.N, L.P)

    # Add resistive load to ground
    R = circuit.AddDevice("Resistor", 40, offset * 3)
    R.Name = f"R_{phase}"
    R.Value = 10     # 10 ohm load
    circuit.AddConnection(L.N, R.P)
    circuit.AddConnection(R.N, gnd.Pin)

# Run the simulation
job = design.TransientAnalysis.NewJob()
status = job.Run()

# Retrieve results for phase A and DC bus input current
time = job.TimePoints
voltage_A = job.GetSignalByName('R_A - Instantaneous Voltage').DataPoints
i_in = job.GetSignalByName('Vdc - Current').DataPoints

# Plot results
plt.figure()
plt.plot(time, voltage_A)
plt.xlabel('Time [s]')
plt.ylabel('Phase A Voltage [V]')
plt.title('Phase A Output Voltage')
plt.grid(True)

plt.figure()
plt.plot(time, i_in)
plt.xlabel('Time [s]')
plt.ylabel('DC Bus Input Current [A]')
plt.title('DC Bus Current')
plt.grid(True)

plt.show()
