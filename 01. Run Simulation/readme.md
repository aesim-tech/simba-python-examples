---
tags:
  - Python Scripts
  - DC-DC
  - Python Basics
---

# Run a simulation with Simba python module

[Download **python script**](1.%20Run%20Simulation.py)


This example launches a simulation of the **Flyback** circuit and plots the output voltage.

The circuit model is directly loaded from the collection of design examples.

![Flyback circuit](fig/flyback.png)

The main steps of this script example are the following:

1. Load python modules: aesim.simba and matplotlib
2. Load the design from the collection of design examples
3. Run a transient simulation
4. Get the output voltage
5. Plot the output voltage depending on time


![Output voltage](fig/output_voltage.png)