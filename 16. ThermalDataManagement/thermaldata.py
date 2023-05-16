#%% Load modules
import os, re
from aesim.simba import ProjectRepository, DesignExamples
import matplotlib.pyplot as plt


#%% plot histogram
def plot_bar(Tab1 = [], 
        Tab2 = [], 
        largeur_barre = 0.3,
        Etiquette = [],
        FigAxe = "ax1",
        show = False,
        plot = plt, Tab1_abscisse = [], 
        dxticks = 0, mxticks = 2, 
        xlim = [], ylim = [],
        color_tab1 = 'orange',
        Legend = ['data 1', 'data 2'],
        ylabel='Average or rms values'):
        """
        Tab1: data 1
        Tab2: data 2
        largeur_barre = 0.3 # Largeur de chaque barre :
        """

        if Tab1_abscisse == []:
                Tab1_abscisse = range(len(Tab1)) # Position des barres de la categorie 1
        
        if Tab2 != []:
                Tab2_abscisse = [i + largeur_barre for i in Tab1_abscisse] # Position des barres de la cat 2

        plot.bar(Tab1_abscisse, Tab1, width = largeur_barre, color = color_tab1, # Barres cat 1
                edgecolor = 'black', linewidth = 2)
        
        if Tab2 != []:
                plot.bar(Tab2_abscisse, Tab2, width = largeur_barre, color = 'yellow', # Barres cat 2
                        edgecolor = ['black' for i in Tab1], linewidth = 2)

        plot.xticks([dxticks+r + largeur_barre / mxticks for r in range(len(Tab1))], # Etiquettes
                Etiquette)

        FigAxe.set_ylabel(ylabel)

        if ylim !=[]:
                plt.ylim(ylim)
        if xlim !=[]:
                plt.xlim(xlim)

        if Tab2 != []:
            plot.legend(Legend)

        if show == True :
                plot.show()

#%% Load project and igbt device
script_folder = os.path.realpath(os.path.dirname(__file__))
file_path = os.path.join(script_folder, "thermal_buck_4pythonexp.jsimba")
project = ProjectRepository(file_path)
design = project.GetDesignByName('Design')
design.TransientAnalysis.StopAtSteadyState = True
igbt = design.Circuit.GetDeviceByName('IGBT1')

igbt_xml_list = [filename for filename in os.listdir('./ThermalDataFile/') if filename.endswith('IGBT.xml')]


#%% Get the job object and solve the system
job = design.TransientAnalysis.NewJob()
status = job.Run()

#%% Get results
t = job.TimePoints
Tj = job.GetSignalByName('IGBT1 - Junction Temperature (°)').DataPoints[-1]
Losses = job.GetSignalByName('IGBT1 - Average Total Losses (W)').DataPoints[-1]

#%% Plot Curve
fig = plt.figure(figsize = (16, 9))
# Losses
ax1 = fig.add_subplot(211)
plot_bar(Tab1 = [Losses], 
        largeur_barre = 0.1,
        Etiquette = [igbt.ThermalData.Name],
        ylabel = 'Losses (W)',
        xlim = [0, 1],
        Tab1_abscisse = [0.5], 
        dxticks= 0.5,
        mxticks = 32,
        FigAxe = ax1)

# Junction temperature
ax2 = fig.add_subplot(212)
plot_bar(Tab1 = [Tj], 
        largeur_barre = 0.1,
        Etiquette = [igbt.ThermalData.Name],
        xlim = [0, 1], ylim = [0, 150],
        Tab1_abscisse = [0.5], 
        dxticks= 0.5,
        mxticks = 32,
        FigAxe = ax2)

# %%
