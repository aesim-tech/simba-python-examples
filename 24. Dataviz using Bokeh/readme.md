---
tags:
  - Python
---

# Data visualization: Use of Bokeh for interactive plots of waveforms and XY graphs

[Download **Python script**](dataviz_bokeh.py)

Bokeh is an interactive visualization library for modern web browsers. It provides elegant, concise construction of versatile graphics and affords high-performance interactivity across large or streaming datasets. 

Bokeh can help anyone who wants to create interactive plots, dashboards, and data applications quickly and easily.

More information about **Bokeh** could be found [here](https://bokeh.org/).


## SIMBA circuit

Below the Dual Active Bridge circuit used for illustrating this Bokeh Python script. This example comes from the existing SIMBA collection of design examples.

![DAB](fig/DAB.png)


## Python Script

The Python script used for showing Bokeh capabilities will do the following tasks:

* Import Bokeh library
* Run a transient analysis of the DCDC Dual Active Bridge Converter and get the output voltage across load resistor $R_{load}$,
* Plot the output voltage with Bokeh and observe the ***time*** and $V_{out}$ values when the signal is highlighted. 

The following syntax **output_notebook()**  is for Jupyter Notebook. In deed, if this line is disable, a new HTML page will be opened showing the result once the script is run. 
If this line is enable, the script needs to be run with interactive cell option.


## Conclusion

Below the simulation result once the script has been executed. 

![result](fig/result2.png)

We can clearly observe time and output voltage values on the figure.

It is also important to say that a valid internet connexion is required when using bokeh library.
