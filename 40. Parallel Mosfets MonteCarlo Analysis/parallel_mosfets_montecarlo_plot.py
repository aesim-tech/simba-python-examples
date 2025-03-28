#%% Load modules
import os
import matplotlib.pyplot as plt
import pandas as pd

# Custom plot functions
def plot(df):

    iterations = range(len(df['Losses11']))

    # Plot figures 
    fig = plt.figure(figsize = (16, 9))

    ax1 = fig.add_subplot(331)
    ax1.plot(iterations, df['Losses11'], linestyle='', color='green', marker='o', markerfacecolor='blue')
    ax1.set_xlabel('iteration', fontsize = 9)
    ax1.set_ylabel('Losses', fontsize = 9)
    ax1.set_title("Losses T11", fontsize = 9)

    ax2 = fig.add_subplot(332)
    ax2.plot(iterations, df['Losses12'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax2.set_xlabel("iteration", fontsize = 9)
    ax2.set_ylabel("Losses", fontsize = 9)
    ax2.set_title("Losses T12", fontsize = 9)

    ax2 = fig.add_subplot(333)
    ax2.plot(iterations, df['Losses13'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax2.set_xlabel("iteration", fontsize = 9)
    ax2.set_ylabel("Losses", fontsize = 9)
    ax2.set_title("Losses T13", fontsize = 9)

    ax5 = fig.add_subplot(334)
    ax5.plot(df['Rdson11'], df['Losses11'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax5.set_xlabel("Rdson", fontsize = 9)
    ax5.set_ylabel("Losses", fontsize = 9)
    ax5.set_title("Losses T11 vs Rdson 11", fontsize = 9)

    ax6 = fig.add_subplot(335)
    ax6.plot(df['Rdson12'], df['Losses11'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax6.set_xlabel("Rdson", fontsize = 9)
    ax6.set_ylabel("Losses", fontsize = 9)
    ax6.set_title("Losses T11 vs Rdson 12", fontsize = 9)

    ax7 = fig.add_subplot(336)
    ax7.plot(df['Rdson13'], df['Losses11'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax7.set_xlabel("Rdson", fontsize = 9)
    ax7.set_ylabel("Losses", fontsize = 9)
    ax7.set_title("Losses T11 vs Rdson 13", fontsize = 9)

    ax5 = fig.add_subplot(337)
    ax5.plot(df['Rdson11'], df['Losses12'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax5.set_xlabel("Rdson", fontsize = 9)
    ax5.set_ylabel("Losses", fontsize = 9)
    ax5.set_title("Losses T12 vs Rdson 11", fontsize = 9)

    ax6 = fig.add_subplot(338)
    ax6.plot(df['Rdson12'], df['Losses12'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax6.set_xlabel("Rdson", fontsize = 9)
    ax6.set_ylabel("Losses", fontsize = 9)
    ax6.set_title("Losses T12 vs Rdson 12", fontsize = 9)

    ax7 = fig.add_subplot(339)
    ax7.plot(df['Rdson13'], df['Losses12'], linestyle='', color='red', marker='o', markerfacecolor='purple')
    ax7.set_xlabel("Rdson", fontsize = 9)
    ax7.set_ylabel("Losses", fontsize = 9)
    ax7.set_title("Losses T12 vs Rdson 13", fontsize = 9)

    fig.tight_layout(pad = 2)
    plt.show()

if os.environ.get("SIMBA_SCRIPT_TEST"): #Excluded from unit test
    exit()
    
# Load dataframe
script_folder = os.path.realpath(os.path.dirname(__file__))
filename = "montecarlo_parallel_mosfets_2025-03-26"
df = pd.read_pickle(os.path.join(script_folder, filename + ".pkl" ))

#%% Plot results from dataframe
plot(df)