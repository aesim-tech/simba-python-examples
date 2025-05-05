#!/usr/bin/env python3
"""
half_bridge_converter.py

Builds and simulates a simple DC/DC half‑bridge converter in SIMBA.
All devices are placed before ANY connection is created.
Every placement is checked; if a spot is already occupied we slide the part
horizontally by 2 units until the placement succeeds, guaranteeing at least
12‑unit clearance around every device (rule #3 & #6).

Author : Emmanuel Rutovic
Date   : 2025‑05‑05
"""

from aesim.simba import Design, ProjectRepository
import os
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Helper that enforces the "placement succeeds or shift" policy
# ---------------------------------------------------------------------------
def safe_add(circ, model_name, x, y, x_shift=2 , y_shift=2):
    """Try AddDevice until it returns a valid device object."""
    dev = circ.AddDevice(model_name, x, y)
    while dev is None:                         # placement collision → slide bottom-right
        x += x_shift
        y += y_shift
        dev = circ.AddDevice(model_name, x, y)
    return dev

# ---------------------------------------------------------------------------
# 1. Create design and analysis setup
# ---------------------------------------------------------------------------
design = Design()
design.Name = "DC/DC - Half-Bridge Converter"
ta = design.TransientAnalysis
ta.TimeStep = 1e-7          # 100 ns
ta.EndTime  = 100e-6        # 100 µs (≈ 10 switching periods at 100 kHz)

circuit = design.Circuit

# ---------------------------------------------------------------------------
# 2. Place ALL devices (respect ≥ 12‑unit spacing)
# ---------------------------------------------------------------------------
# Coordinates picked on a loose 20‑unit grid; safe_add will slide if needed.

# — 2.1 Sources & grounds ----------------------------------------------------
vdc   = safe_add(circuit, "DC Voltage Source", 0,   0)   # Width 4, Height 8
vdc.Voltage = 48                                          # 48 V input
for s in vdc.Scopes:                                 # enable V/I scopes for post‑proc
    s.Enabled = True

gnd_1 = safe_add(circuit, "Ground",          0,  10)      # local input ground

# — 2.2 PWM generator & inverter --------------------------------------------
pwm   = safe_add(circuit, "Square Wave",     0,  30)
pwm.Frequency  = 100e3                                   # 100 kHz switching
pwm.DutyCycle  = 0.5                                     # 50 % duty
pwm.Amplitude  = 1

invert = safe_add(circuit, "Not",           10,  30)

# — 2.3 Power switches (vertical MOSFETs with body diode) --------------------
q_high = safe_add(circuit, "Ideal MOSFET with Diode", 20,   0)   # Q_H
q_low  = safe_add(circuit, "Ideal MOSFET with Diode", 20,  18)   # Q_L (≥12 units below)

# — 2.4 Output filter & load -------------------------------------------------
ind   = safe_add(circuit, "Inductor",        20,   4)
ind.Value = 10e-6                            # 10 µH

cap   = safe_add(circuit, "Capacitor",       30,   4)
cap.Value = 220e-6                           # 220 µF
cap.RotateRight()                            # horizontal pins

res   = safe_add(circuit, "Resistor",        40,  4)
res.Value = 4                                # 4 Ω load
res.RotateRight()
res.Name = "R_load"
for s in res.Scopes:                         # enable V/I scopes for post‑proc
    s.Enabled = True

gnd_2 = safe_add(circuit, "Ground",         35,  12)      # local output ground

# ---------------------------------------------------------------------------
# 3. Create ALL connections (after every device is placed)
# ---------------------------------------------------------------------------

# — 3.1 Input side -----------------------------------------------------------
circuit.AddConnection(vdc.P, q_high.Drain)         # Vdc+ → high‑side drain
circuit.AddConnection(vdc.N, gnd_1.Pin)            # Vdc‑ → ground

# — 3.2 Half‑bridge node -----------------------------------------------------
circuit.AddConnection(q_high.Source, q_low.Drain)  # common mid‑point
circuit.AddConnection(q_low.Source, gnd_1.Pin)     # low‑side source to ground

# — 3.3 Gate drives ----------------------------------------------------------
circuit.AddConnection(pwm.Out,     q_high.Gate)    # PWM → Q_H gate
circuit.AddConnection(pwm.Out,     invert.In)      # PWM → Not
circuit.AddConnection(invert.Out,  q_low.Gate)     # Not → Q_L gate

# — 3.4 Output filter / load -------------------------------------------------
circuit.AddConnection(q_high.Source, ind.P)        # mid‑point → inductor
circuit.AddConnection(ind.N, cap.P)                # L → C (+)
circuit.AddConnection(ind.N, res.P)                # L → load
circuit.AddConnection(cap.N, gnd_2.Pin)            # C (−) → output gnd
circuit.AddConnection(res.N, gnd_2.Pin)            # load (−) → output gnd

# ---------------------------------------------------------------------------
# 4. Run transient simulation
# ---------------------------------------------------------------------------
job    = ta.NewJob()
status = job.Run()
assert str(status) == 'OK', job.Summary()

# ---------------------------------------------------------------------------
# 5. Post‑processing (note: each signal owns its own TimePoints vector)
# ---------------------------------------------------------------------------
for s in job.Signals:
    print(f"{s.Name}")
v_out = job.GetSignalByName("R_load - Instantaneous Voltage")
i_in  = job.GetSignalByName("DC1 - Current")

plt.figure()
plt.plot(v_out.TimePoints, v_out.DataPoints)
plt.xlabel("Time [s]")
plt.ylabel("Vout [V]")
plt.title("Half‑Bridge Output Voltage (after LC filter)")
plt.grid(True)

plt.figure()
plt.plot(i_in.TimePoints, i_in.DataPoints)
plt.xlabel("Time [s]")
plt.ylabel("Input Current [A]")
plt.title("DC Bus Input Current")
plt.grid(True)

plt.show()

# ---------------------------------------------------------------------------
# 6. Save project
# ---------------------------------------------------------------------------
filepath = os.path.join(os.getcwd(), "HB.jsimba")
if os.path.isfile(filepath):
    os.remove(filepath)
proj = ProjectRepository(filepath)
proj.AddDesign(design)
proj.Save()
print(f"Design saved to: {filepath}")