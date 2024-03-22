#%% Load modules
from aesim.simba import DesignExamples
from bokeh.plotting import figure
from bokeh.io import show, output_notebook

#%% Load SIMBA project
forward = DesignExamples.DCDC_Forward_Converter()

#%% Config the solver, get the job object,  solve the system
forward.TransientAnalysis.StopAtSteadyState = True
forward.TransientAnalysis.BaseFrequencyParameterEnabled = True
forward.TransientAnalysis.BaseFrequency = 200e3
forward.TransientAnalysis.NumberOfBasePeriodsSavedParameterEnabled = True
forward.TransientAnalysis.NumberOfBasePeriodsSaved = 4
job = forward.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
Vds = job.GetSignalByName('T1 - Voltage').DataPoints

#%% Plot Curve

TOOLTIPS = [       #allows to display interactively t and vout values by using x and y position.
    ("index", "$index"),
    ("(t, Vmosfet)", "($x, $y)"),
    ]
p = figure(title=" converter", 
           x_axis_label='time (s)', 
           y_axis_label='Vds (V)',
           active_drag='box_zoom',
           tooltips = TOOLTIPS)
p.line(t, Vds, legend_label="Mosfet Vds voltage", line_width=1)
p.legend.location = "bottom_right"
#output_notebook()  # For Jupyter Notebook: if this line is disable, a new HTML page will be opened showing the result. If this line is enable, run the script with interactive cell
show(p)
