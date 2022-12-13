'''
    File : DistributionPV.py
    Author: Maxime Félix
    Created : 19.05.2022
    Updated : 28.07.2022
    Lecture : Travail de Bachelor
    Purpose : Pseudo-real time simulation interface
'''

# Load required module
from aesim.simba import Design, ProjectRepository, DesignExamples

import sys
import matplotlib.pyplot as plt
import os, pathlib
from tkinter import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import matplotlib.animation as animation

# variables
is_on_1 = False
is_on_2 = False
is_on_3 = False
is_on_4 = False
variable_soc='0%'
tableau_data_I = []
tableau_t_I = []
tableau_t_I_all = []
tableau_I_PV = []
tableau_I_bat = []
tableau_I_AFE = []
tableau_I_charge = []

tableau_data_V = []
tableau_t_V = []
tableau_t_V_all = []
tableau_V_PV = []
tableau_V_bat = []
tableau_V_AFE = []
tableau_V_charge = []

def circuit():
    # Obtention du projet
    filepath = os.path.join(os.path.dirname(__file__), "DistributionPV.simba")
    print("loading model: " + filepath)
    # Ouverture du projet
    project = ProjectRepository(filepath)
    DistributionPV = project.GetDesignByName("DistributionPV")
    # Définition des simulations
    DistributionPV.TransientAnalysis.NumberOfPointsToSimulate = 1000
    job = DistributionPV.TransientAnalysis.NewJob()
    # Grandeurs modifiée
    Soleil = DistributionPV.Circuit.GetDeviceByName('Sun_Value')
    Charge_valeur = DistributionPV.Circuit.GetDeviceByName('Load_Value')
    retour = [job,Soleil,Charge_valeur]

    return retour
def initialisation_graphe():
    # Définition des grpahiques
    fig, (ax1, ax2) = plt.subplots(2, 1)
    # Attribution des lignes au graphiques
    ln_I, = ax1.plot([], [])
    ln_I_PV, = ax1.plot([], [])
    ln_I_AFE, = ax1.plot([], [])
    ln_I_charge, = ax1.plot([], [])
    ln_I_bat, = ax1.plot([], [])

    ln_V, = ax2.plot([], [])
    ln_V_PV, = ax2.plot([], [])
    ln_V_AFE, = ax2.plot([], [])
    ln_V_charge, = ax2.plot([], [])
    ln_V_bat, = ax2.plot([], [])

    # Paramètres des axes
    ax1.set_title('Simulation pseudo-temps réel')
    ax1.set_ylabel('I_AFE (A)')
    ax1.set_ylim(-1000, 1000)
    ax1.grid(True)

    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('V_AFE (V)')
    ax2.set_ylim(1900, 2100)
    ax2.grid(True)
    return ax1,ax2,fig,ln_I, ln_I_PV,ln_I_AFE,ln_I_charge,ln_I_bat,ln_V,ln_V_PV,ln_V_AFE,ln_V_charge,ln_V_bat
def calcul():
    status = job.Run()
    # Current data
    I_AFE = np.array(job.GetSignalByName('Sc3:I_AFE - Instantaneous Current').DataPoints)
    I_PV = np.array(job.GetSignalByName('Sc3:I_PV - Instantaneous Current').DataPoints)
    I_BATT = np.array(job.GetSignalByName('Sc3:I_BATT - Instantaneous Current').DataPoints)
    I_LOAD = np.array(job.GetSignalByName('Sc3:I_LOAD - Instantaneous Current').DataPoints)
    # Voltage data
    V_AFE = np.array(job.GetSignalByName('Sc3:V_AFE - Instantaneous Voltage').DataPoints)
    V_PV = np.array(job.GetSignalByName('Sc3:V_PV - Instantaneous Voltage').DataPoints)
    V_BATT = np.array(job.GetSignalByName('Sc3:V_BAT - Instantaneous Voltage').DataPoints)
    V_LOAD = np.array(job.GetSignalByName('Sc3:V_LOAD - Instantaneous Voltage').DataPoints)
    #Time
    t = np.array(job.TimePoints)
    # soc
    soc = np.array(job.GetSignalByName('Sc5:mesure_soc - Instantaneous Current').DataPoints)
    soc_filtre = round(soc[-1]*100,0)
    variable_soc = str(soc_filtre)+'%'
    label_soc['text']=variable_soc
    job.ClearScopesData()
    return [t,I_AFE,I_PV,I_BATT,I_LOAD,V_AFE,V_PV,V_BATT,V_LOAD]
def Charge_1():
    # définition de la variable global modifiable
    global is_on_1
    # conditions d'activation
    if is_on_1:
        canvas_Charge_1.itemconfigure(image_charge_1,image=image_Repas_verte)
        is_on_1 = False
        Charge_valeur.Value = Charge_valeur.Value - 0.4
    else:
        canvas_Charge_1.itemconfigure(image_charge_1,image=image_Repas_rouge)
        is_on_1 = True
        Charge_valeur.Value = Charge_valeur.Value + 0.4
def Charge_2():
    # définition de la variable global modifiable
    global is_on_2
    # conditions d'activation
    if is_on_2:
        canvas_Charge_2.itemconfigure(image_charge_2,image=image_Machine_verte)
        is_on_2 = False
        Charge_valeur.Value = Charge_valeur.Value - 0.3
    else:
        canvas_Charge_2.itemconfigure(image_charge_2,image=image_Machine_rouge)
        is_on_2 = True
        Charge_valeur.Value = Charge_valeur.Value + 0.3
def Charge_3():
    # définition de la variable global modifiable
    global is_on_3
    # conditions d'activation
    if is_on_3:
        canvas_Charge_3.itemconfigure(image_charge_3,image=image_Chauffage_verte)
        is_on_3 = False
        Charge_valeur.Value = Charge_valeur.Value - 0.2
    else:
        canvas_Charge_3.itemconfigure(image_charge_3,image=image_Chauffage_rouge)
        is_on_3 = True
        Charge_valeur.Value = Charge_valeur.Value + 0.2
def Charge_4():
    # définition de la variable global modifiable
    global is_on_4
    # conditions d'activation
    if is_on_4:
        canvas_Charge_4.itemconfigure(image_charge_4,image=image_Lampe_verte)
        is_on_4 = False
        Charge_valeur.Value = Charge_valeur.Value - 0.1
    else:
        canvas_Charge_4.itemconfigure(image_charge_4,image=image_Lampe_rouge)
        is_on_4 = True
        Charge_valeur.Value = Charge_valeur.Value + 0.1
def incrementation():
    # Récuperation de la valeur d'ensoleillement
    value = int(label_incrementation["text"])
    # Conditions d'incrementation
    if value < 3:
        value = value + 1
        label_incrementation["text"] = f"{value}"
    else:
        value = 3
        label_incrementation["text"] = f"{value}"
    # Conditions pour les images et la valeur d'ensoleillement
    if value == 3:
        canvas_ensoleillement.itemconfigure(image_ensoleillement,image=image_soleil)
        Soleil.Value = 1
    elif value == 2:
        canvas_ensoleillement.itemconfigure(image_ensoleillement,image=image_soleil_nuage)
        Soleil.Value = 0.5
    else:
        canvas_ensoleillement.itemconfigure(image_ensoleillement,image=image_nuage)
        Soleil.Value = 0
def decrementation():
    # Récuperation de la valeur d'ensoleillement
    value = int(label_incrementation["text"])
    # condition de décrémentation
    if value > 1:
        value = value - 1
        label_incrementation["text"] = f"{value}"
    else:
        value = 1
        label_incrementation["text"] = f"{value}"
    # conditions pour les images et la valeur d'ensoleillement
    if value == 3:
        canvas_ensoleillement.itemconfigure(image_ensoleillement, image=image_soleil)
        Soleil.Value = 1
    elif value == 2:
        canvas_ensoleillement.itemconfigure(image_ensoleillement, image=image_soleil_nuage)
        Soleil.Value = 0.5
    else:
        canvas_ensoleillement.itemconfigure(image_ensoleillement, image=image_nuage)
        Soleil.Value = 0
def affichage(i):
    # récupération du mode choisi
    grandeur_simuler_I = variable_Current.get()
    grandeur_simuler_V = variable_Voltage.get()
    # calcul des grandeurs
    [t, I_AFE, I_PV, I_BATT, I_LOAD, V_AFE, V_PV, V_BATT, V_LOAD] = calcul()
    # Current data
    # Cas affichage tout les courants
    if grandeur_simuler_I == 'Courant':
        # Nettoyage des tableaux des courants afficher en solo
        if len(tableau_t_I) > 0:
            tableau_t_I.clear()
            tableau_data_I.clear()
            ln_I.set_data(tableau_t_I, tableau_data_I)
        # Remplissage des tableaux avec tailles d'une mesures (1000 points)
        for i in range(len(I_AFE)):
            tableau_t_I_all.append(t[i])
            tableau_I_AFE.append(I_AFE[i])
            tableau_I_PV.append(I_PV[i])
            tableau_I_bat.append(I_BATT[i])
            tableau_I_charge.append(I_LOAD[i])
        # Supression des premieres valeurs du tableaux du même nombre rentrant
        if (len(tableau_t_I_all) > 25000):
            del tableau_t_I_all[0:len(t)]
            del tableau_I_AFE[0:len(I_AFE)]
            del tableau_I_PV[0:len(I_PV)]
            del tableau_I_bat[0:len(I_BATT)]
            del tableau_I_charge[0:len(I_LOAD)]
        # Actualisation des données
        ln_I_PV.set_data(tableau_t_I_all, tableau_I_PV)
        ln_I_charge.set_data(tableau_t_I_all, tableau_I_charge)
        ln_I_bat.set_data(tableau_t_I_all, tableau_I_bat)
        ln_I_AFE.set_data(tableau_t_I_all, tableau_I_AFE)
        # Actualisation label et légende
        ax1.set_ylabel('Courant (A)')
        ax1.legend([ln_I_PV,ln_I_charge,ln_I_bat,ln_I_AFE],['I_PV','I_LOAD','I_BATT','I_AFE'])
    # cas courant séparé
    else:
        # Suppression et actualisation tableau de l'affichage complet
        if len(tableau_I_AFE) > 0:
            tableau_I_AFE.clear()
            tableau_I_bat.clear()
            tableau_I_PV.clear()
            tableau_I_charge.clear()
            tableau_t_I_all.clear()
            ln_I_AFE.set_data(tableau_t_I_all, tableau_I_AFE)
            ln_I_bat.set_data(tableau_t_I_all, tableau_I_bat)
            ln_I_PV.set_data(tableau_t_I_all, tableau_I_PV)
            ln_I_charge.set_data(tableau_t_I_all, tableau_I_charge)
            ax1.get_legend().remove()
        # Conditions affichage singulier
        if grandeur_simuler_I == 'Courant AFE':
            Iout = I_AFE
            ax1.set_ylabel('I_AFE(A)')
        elif grandeur_simuler_I == 'Courant PV':
            Iout = I_PV
            ax1.set_ylabel('I_PV(A)')
        elif grandeur_simuler_I == 'Courant charge':
            Iout = I_LOAD
            ax1.set_ylabel('I_LOAD(A)')
        elif grandeur_simuler_I == 'Courant Bat':
            Iout = I_BATT
            ax1.set_ylabel('I_BATT(A)')
        else:
            Iout = I_AFE
            ax1.set_ylabel('I_AFE(A)')
        # Remplissage des tableaux avec tailles d'une mesures (1000 points)
        for i in range(len(Iout)):
            tableau_t_I.append(t[i])
            tableau_data_I.append(Iout[i])
        # Supression des premieres valeurs du tableaux du même nombre rentrant
        if (len(tableau_t_I) > 25000):
            del tableau_t_I[0:len(t)]
            del tableau_data_I[0:len(Iout)]
        ln_I.set_data(tableau_t_I, tableau_data_I)
    # limitation de l'abscisse
    ax1.relim()
    ax1.autoscale_view(scalex=True, scaley=False)

    # Voltage data
    # Cas affichage toutes les tensions
    if grandeur_simuler_V == 'Tension':
        # Nettoyage des tableaux des courants afficher en solo
        if len(tableau_t_V) > 0:
            tableau_t_V.clear()
            tableau_data_V.clear()
            ln_V.set_data(tableau_t_V, tableau_data_V)
        # Remplissage des tableaux avec tailles d'une mesures (1000 points)
        for i in range(len(V_AFE)):
            tableau_t_V_all.append(t[i])
            tableau_V_AFE.append(V_AFE[i])
            tableau_V_PV.append(V_PV[i])
            tableau_V_bat.append(V_BATT[i])
            tableau_V_charge.append(V_LOAD[i])
        # Supression des premieres valeurs du tableaux du même nombre rentrant
        if (len(tableau_t_V_all) > 25000):
            del tableau_t_V_all[0:len(t)]
            del tableau_V_AFE[0:len(V_AFE)]
            del tableau_V_PV[0:len(V_PV)]
            del tableau_V_bat[0:len(V_BATT)]
            del tableau_V_charge[0:len(V_LOAD)]
        # Actualisation des données
        ln_V_PV.set_data(tableau_t_V_all, tableau_V_PV)
        ln_V_charge.set_data(tableau_t_V_all, tableau_V_charge)
        ln_V_bat.set_data(tableau_t_V_all, tableau_V_bat)
        ln_V_AFE.set_data(tableau_t_V_all, tableau_V_AFE)
        # Actualisation label et légende
        ax2.set_ylabel('Tension (V)')
        ax2.legend([ln_V_PV,ln_V_charge,ln_V_bat,ln_V_AFE],['V_PV','V_LOAD','V_BATT','V_AFE'])
    # cas tension séparés
    else:
        # Suppression et actualisation tableau de l'affichage complet
        if len(tableau_V_AFE) > 0:
            tableau_V_AFE.clear()
            tableau_V_bat.clear()
            tableau_V_PV.clear()
            tableau_V_charge.clear()
            tableau_t_V_all.clear()
            ln_V_AFE.set_data(tableau_t_V_all, tableau_V_AFE)
            ln_V_bat.set_data(tableau_t_V_all, tableau_V_bat)
            ln_V_PV.set_data(tableau_t_V_all, tableau_V_PV)
            ln_V_charge.set_data(tableau_t_V_all, tableau_V_charge)
            ax2.get_legend().remove()
        # Conditions affichage singulier
        if grandeur_simuler_V == 'Tension AFE':
            Vout = V_AFE
            ax2.set_ylabel('V_AFE(V)')
        elif grandeur_simuler_V == 'Tension PV':
            Vout = V_PV
            ax2.set_ylabel('V_PV(V)')
        elif grandeur_simuler_V == 'Tension charge':
            Vout = V_LOAD
            ax2.set_ylabel('V_LOAD(V)')
        elif grandeur_simuler_V == 'Tension Bat':
            Vout = V_BATT
            ax2.set_ylabel('V_BATT(V)')
        else:
            Vout = V_AFE
            ax2.set_ylabel('V_AFE(V)')
        # Remplissage des tableaux avec tailles d'une mesures (1000 points)
        for i in range(len(Vout)):
            tableau_t_V.append(t[i])
            tableau_data_V.append(Vout[i])
        # Supression des premieres valeurs du tableaux du même nombre rentrant
        if (len(tableau_t_V) > 25000):
            del tableau_t_V[0:len(t)]
            del tableau_data_V[0:len(Vout)]
        ln_V.set_data(tableau_t_V, tableau_data_V)
    # relimitation de l'abscisse
    ax2.relim()
    ax2.autoscale_view(scalex=True, scaley=False)
def quitter():
    sys.exit()

# Initialisation circuit et simulation
[job,Soleil,Charge_valeur] = circuit()

# creer la fenetre
fenetre = Tk()

# parametre fenetre
fenetre.title('interface')
fenetre.geometry('1000x680')
fenetre.minsize(480, 360)
def image_path(image_filename): return os.path.join(os.path.dirname(__file__), "Image",image_filename)
fenetre.iconbitmap(image_path("logo_HEIG.ico"))
fenetre.config(background='white')
largeur = 150
hauteur = 150

# configuration grille
fenetre.rowconfigure(0,weight=1)
fenetre.rowconfigure(1,weight=1)
fenetre.columnconfigure(0,weight=1)
fenetre.columnconfigure(1,weight=1)
fenetre.columnconfigure(2,weight=4)

# création des cases
case_ensoleillement = Frame(fenetre)
case_incrementation_ensol = Frame(fenetre)
case_batterie = Frame(fenetre)
case_interaction_batterie= Frame(fenetre)
case_charge = Frame(fenetre)
case_interaction= Frame(fenetre)
case_graphique = Frame(fenetre)
case_choix_I = Frame(case_graphique)
case_choix_V = Frame(case_graphique)

# Positionement cases
case_ensoleillement.grid(row=0, column=0,sticky='NSEW',pady=10)
case_incrementation_ensol.grid(row=0, column=0,sticky='S',pady=15)
case_batterie.grid(row=0, column=1,sticky='NSEW',pady=10,padx=10)
case_interaction_batterie.grid(row=0, column=1,sticky='S',pady=15)
case_charge.grid(row=1, column=0,sticky='NSEW',columnspan=2,padx=(0,10))
case_interaction.grid(row=1, column=1,sticky='S',pady=15)
case_graphique.grid(row=0, column=2,rowspan= 2,sticky='NSEW')

# Configuration cases
case_incrementation_ensol.rowconfigure(0, minsize=50, weight=1)
case_incrementation_ensol.columnconfigure([0, 1, 2], minsize=50, weight=1)

# création des labels
label_ensoleillement = Label(fenetre,text="Ensoleillement",fg="black",font=("Helvetica", 18))
label_incrementation = Label(case_incrementation_ensol, text="1")
label_batterie = Label(fenetre,text="Etat de charge batterie",fg="black",font=("Helvetica", 18))
label_charge = Label(fenetre,text="Niveau de charge",fg="black",font=("Helvetica", 18))
label_simulation = Label(case_graphique,text="Simulation",fg="black",font=("Helvetica", 18))
label_soc = Label(fenetre,text=variable_soc,fg="black",font=("Helvetica", 32))

# Positionnement label
label_ensoleillement.grid(row=0, column=0,sticky='NEW')
label_incrementation.grid(row=0, column=1)
label_batterie.grid(row=0, column=1,sticky='NEW',padx=10)
label_charge.grid(row=1, column=0,columnspan=2,sticky='N')
label_simulation.pack()
case_choix_I.pack(pady=10)
label_choix_I = Label(case_choix_I,text="Courant a simuler",fg="black",font=("Helvetica", 12))
label_choix_I.pack(side=LEFT)
case_choix_V.pack(pady=10)
label_choix_V = Label(case_choix_V,text="Tension a simuler",fg="black",font=("Helvetica", 12))
label_choix_V.pack(side=LEFT)
label_soc.grid(row=0, column=1)

# image

image_soleil = PhotoImage(file=image_path("soleil.png")).subsample(2)
image_nuage = PhotoImage(file=image_path("nuage.png")).subsample(2)
image_soleil_nuage = PhotoImage(file=image_path("soleil_nuage.png")).subsample(2)
image_Lampe_verte = PhotoImage(file=image_path("Lampe_Verte.png")).zoom(10).subsample(25)
image_Lampe_rouge = PhotoImage(file=image_path("Lampe_Rouge.png")).zoom(10).subsample(25)
image_Machine_verte = PhotoImage(file=image_path("Machine_Verte.png")).zoom(10).subsample(25)
image_Machine_rouge = PhotoImage(file=image_path("Machine_Rouge.png")).zoom(10).subsample(25)
image_Chauffage_verte = PhotoImage(file=image_path("Chaleur_Verte.png")).zoom(10).subsample(25)
image_Chauffage_rouge = PhotoImage(file=image_path("Chaleur_Rouge.png")).zoom(10).subsample(25)
image_Repas_verte = PhotoImage(file=image_path("Repas_Vert.png")).zoom(10).subsample(25)
image_Repas_rouge = PhotoImage(file=image_path("Repas_Rouge.png")).zoom(10).subsample(25)

# création canvas images
canvas_ensoleillement = Canvas(fenetre, width=largeur, height=hauteur,bg='white')
canvas_Charge_1 = Canvas(case_charge, width=largeur, height=hauteur,bg='white')
canvas_Charge_2 = Canvas(case_charge, width=largeur, height=hauteur,bg='white')
canvas_Charge_3 = Canvas(case_charge, width=largeur, height=hauteur,bg='white')
canvas_Charge_4 = Canvas(case_charge, width=largeur, height=hauteur,bg='white')

# attribution image au canvas
image_ensoleillement = canvas_ensoleillement.create_image(largeur / 2, hauteur / 2, image=image_nuage)
image_charge_1 = canvas_Charge_1.create_image(largeur / 2, hauteur / 2, image=image_Repas_verte)
image_charge_2 = canvas_Charge_2.create_image(largeur / 2, hauteur / 2, image=image_Machine_verte)
image_charge_3 = canvas_Charge_3.create_image(largeur / 2, hauteur / 2, image=image_Chauffage_verte)
image_charge_4 = canvas_Charge_4.create_image(largeur / 2, hauteur / 2, image=image_Lampe_verte)

# Positionement canvas
canvas_ensoleillement.grid(row=0, column=0)
case_charge.rowconfigure(0,weight=1)
case_charge.columnconfigure(0,weight=1)
case_charge.columnconfigure(1,weight=1)
case_charge.columnconfigure(2,weight=1)
case_charge.columnconfigure(3,weight=1)
canvas_Charge_1.grid(row=0,column=0)
canvas_Charge_2.grid(row=0,column=1)
canvas_Charge_3.grid(row=0,column=2)
canvas_Charge_4.grid(row=0,column=3)

#configuration choix
choix_I = ['Courant AFE','Courant PV','Courant charge','Courant Bat','Courant']
variable_Current = StringVar(case_choix_I)
variable_Current.set('Courant AFE')

choix_V = ['Tension AFE','Tension PV','Tension charge','Tension Bat','Tension']
variable_Voltage = StringVar(case_choix_V)
variable_Voltage.set('Tension AFE')

# création widget (interaction)
bouton_incrementation = Button(case_incrementation_ensol, text="+", command=incrementation)
bouton_decrementation = Button(case_incrementation_ensol, text="-", command=decrementation)
bouton_quitter = Button(case_graphique,bg='red',height=5,width = 15,text='Quitter',command=quitter)
bouton_choix_I = OptionMenu(case_choix_I, variable_Current, *choix_I)
bouton_choix_V = OptionMenu(case_choix_V, variable_Voltage, *choix_V)
bouton_charge_1 = Button(case_charge,text='Diner',height=5,font=("Helvetica", 15),command=Charge_1)
bouton_charge_2 = Button(case_charge,text='Machine',height=5,font=("Helvetica", 15),command=Charge_2)
bouton_charge_3 = Button(case_charge,text='Chauffage',height=5,font=("Helvetica", 15),command=Charge_3)
bouton_charge_4 = Button(case_charge,text='Éclairage',height=5,font=("Helvetica", 15),command=Charge_4)

# Positionement widget
bouton_decrementation.grid(row=0, column=0, sticky="nsew")
bouton_incrementation.grid(row=0, column=2, sticky="nsew")
bouton_charge_1.grid(row=0, column=0, sticky="SEW",pady=10,padx=5)
bouton_charge_2.grid(row=0, column=1, sticky="SEW",pady=10,padx=5)
bouton_charge_3.grid(row=0, column=2, sticky="SEw",pady=10,padx=5)
bouton_charge_4.grid(row=0, column=3, sticky="SEW",pady=10,padx=5)
bouton_quitter.pack(side= BOTTOM,pady=15)
bouton_choix_I.pack()
case_choix_I.pack()
bouton_choix_V.pack()
case_choix_V.pack()

# paramètre graphique
[ax1,ax2,fig,ln_I, ln_I_PV,ln_I_AFE,ln_I_charge,ln_I_bat,ln_V,ln_V_PV,ln_V_AFE,ln_V_charge,ln_V_bat] = initialisation_graphe()
canvas_graphique = FigureCanvasTkAgg(fig, case_graphique)
canvas_graphique.get_tk_widget().pack(padx=10, pady=10, expand=YES)
ani = animation.FuncAnimation(fig, affichage, interval=1000)

# afficher la fenetre
fenetre.mainloop()