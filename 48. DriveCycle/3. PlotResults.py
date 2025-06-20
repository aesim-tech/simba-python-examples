#!/usr/bin/env python
"""
Quick-look plots of inverter + motor performance over the drive-cycle.
"""

import os, pandas as pd, matplotlib.pyplot as plt

HERE      = os.path.abspath(os.path.dirname(__file__))
RESULT_PKL = os.path.join(HERE, "drive_cycle_results.pkl")

def main():
    df = pd.read_pickle(RESULT_PKL)
    if df.empty:
        raise RuntimeError("Results file is empty or missing.")

    t = df["time_s"]

    fig, axs = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    fig.suptitle("Electric Drive – Drive-cycle summary")

    # 1) total losses
    axs[0].plot(t, df["total_loss_W"])
    axs[0].set_ylabel("Total losses [W]")
    axs[0].grid(True)

    # 2) efficiency
    axs[1].plot(t, df["efficiency_pct"])
    axs[1].set_ylabel("Efficiency [%]")
    axs[1].set_ylim(0, 100)
    axs[1].grid(True)

    # 3) junction temperature
    axs[2].plot(t, df["Tj_C"])
    axs[2].set_ylabel("Tj [°C]")
    axs[2].set_xlabel("Time [s]")
    axs[2].grid(True)

    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

if __name__ == "__main__":
    main()