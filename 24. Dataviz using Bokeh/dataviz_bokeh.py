#%% Load modules
from aesim.simba import DesignExamples
from bokeh.plotting import figure
from bokeh.io import show, output_notebook

#%% Load project
DAB = DesignExamples.DCDC_Dual_Active_Bridge_Converter()

#%% Get the job object and solve the system
job = DAB.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
Vout = job.GetSignalByName('Vout - Out').DataPoints

#%% Plot Curve

TOOLTIPS = [       #allows to display interactively t and vout values by using x and y position.
    ("index", "$index"),
    ("(t, vout)", "($x, $y)"),
    ]
p = figure(title="Dual Active Bridge", 
           x_axis_label='time (s)', 
           y_axis_label='Vout (V)',
           tooltips = TOOLTIPS)
p.line(t, Vout, legend_label="Output voltage", line_width=4)
p.legend.location = "bottom_right"
#output_notebook()  # For Jupyter Notebook: if this line is disable, a new HTML page will be opened showing the result. If this line is enable, run the script with interactive cell
show(p)

# %%