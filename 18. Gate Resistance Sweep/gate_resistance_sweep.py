#%% Load modules
import os
from aesim.simba import ProjectRepository
import matplotlib.pyplot as plt
import matplotlib as mpl


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
        xlabel='',
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

        plot.xticks([dxticks + r - largeur_barre / mxticks for r in range(len(Tab1))], # Etiquettes
                Etiquette, rotation = 0)
        FigAxe.set_xlabel(xlabel)
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
file_path = os.path.join(script_folder, "thermal_buck_Rg_4python.jsimba")
project = ProjectRepository(file_path)
design = project.GetDesignByName('Design')
# design = DesignExamples.Buck_Thermal()
design.TransientAnalysis.StopAtSteadyState = True
mosfet = design.Circuit.GetDeviceByName('MOSFET1')
for scope in mosfet.Scopes:
    if scope.Name == 'Junction Temperature (°)' or scope.Name == 'Average Total Losses (W)':
        scope.Enabled = True

junction_temps = []
Losses = []
#%% Create list of gate resistances an run simulations
Rg_list = [1, 2.5, 5, 10]
for Rg in Rg_list:    
    mosfet.CustomVariables[0].Value = str(Rg)
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    Tj = job.GetSignalByName('MOSFET1 - Junction Temperature (°)').DataPoints[-1]
    Loss = job.GetSignalByName('MOSFET1 - Average Total Losses (W)').DataPoints[-1]
    junction_temps.append(Tj)
    Losses.append(Loss)


#%% Plot data
mpl.rcParams['font.size'] = 15  # Set the default font 
fig = plt.figure(figsize = (16, 16))
# Losses
ax1 = fig.add_subplot(211)
plot_bar(Tab1 = Losses, 
        largeur_barre = 0.1,
        Etiquette = [str(Rg) for Rg in Rg_list],
        xlabel = 'Gate resistances (Ohms)',
        ylabel = 'Losses (W)',
        mxticks = 32,
        FigAxe = ax1)
plt.subplots_adjust(hspace = 0.4)

# Junction temperature
ax2 = fig.add_subplot(212)
plot_bar(Tab1 = junction_temps, 
        largeur_barre = 0.1,
        Etiquette = [str(Rg) for Rg in Rg_list],
        xlabel = 'Gate resistances (Ohms)',
        ylabel='Junction temperatures (°)',
        mxticks = 32,
        FigAxe = ax2)
# %%