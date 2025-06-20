#!/usr/bin/env python
"""
Enhanced quick-look plots of inverter + motor performance over the drive-cycle.

• Vehicle speed in km/h
• Separate curves for inverter and motor losses (with light fill)
• Efficiency and junction temperature

Make sure the drivetrain constants (GEAR_RATIO, WHEEL_RADIUS_M) match those
used in *PrepareData.py* and *DriveCycle.py* so that the speed computation is
consistent.
"""

from __future__ import annotations
import math
import os

import matplotlib.pyplot as plt
import pandas as pd

# ──────────────────────────────────────────────────────────── CONSTANTS ────── #
HERE = os.path.abspath(os.path.dirname(__file__))
RESULT_PKL = os.path.join(HERE, "drive_cycle_results.pkl")

# Vehicle / driveline parameters (must reflect simulation settings)
GEAR_RATIO = 7.0            # Total reduction wheel ← motor (dimensionless)
WHEEL_RADIUS_M = 0.30       # [m]


# ────────────────────────────────────────────────────────────── HELPERS ────── #

def _rpm_to_kph(rpm_series: pd.Series | pd.ArrayLike) -> pd.Series:
    """Convert motor RPM to vehicle speed in km/h."""
    omega_motor = rpm_series * 2.0 * math.pi / 60.0        # rad/s
    omega_wheel = omega_motor / GEAR_RATIO                 # rad/s
    v_mps = omega_wheel * WHEEL_RADIUS_M                   # m/s
    return v_mps * 3.6                                     # km/h


# ─────────────────────────────────────────────────────────────── MAIN ────── #

def main() -> None:
    df = pd.read_pickle(RESULT_PKL)
    if df.empty:
        raise RuntimeError("Results file is empty or missing – run 2.DriveCycle.py first.")

    # ── Prepare time axis ──────────────────────────────────────────────────── #
    t = df["time_s"]

    # ── Vehicle speed (km/h) ───────────────────────────────────────────────── #
    if "speed_kph" in df.columns:
        v_kph = df["speed_kph"]
    else:
        # Prefer actual measured speed, fall back to commanded speed
        if "actual_speed_rpm" in df.columns:
            rpm_src = df["actual_speed_rpm"]
        elif "motor_rpm_cmd" in df.columns:
            rpm_src = df["motor_rpm_cmd"]
        else:
            raise KeyError("No RPM column found to derive vehicle speed.")
        v_kph = _rpm_to_kph(rpm_src)
        df["speed_kph"] = v_kph  # cache for future runs

    # ── Matplotlib appearance tweaks ──────────────────────────────────────── #
    plt.style.use("ggplot")
    plt.rcParams.update({
        "axes.grid"      : True,
        "grid.linestyle" : ":",
        "grid.linewidth" : 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })

    # ── Figure layout ─────────────────────────────────────────────────────── #
    fig, axs = plt.subplots(
        4, 1, figsize=(12, 10), sharex=True,
        gridspec_kw={"hspace": 0.25}
    )
    fig.suptitle("Electric Drive – Drive-cycle summary", fontsize=16, weight="bold")

    # 1) Vehicle speed ------------------------------------------------------- #
    axs[0].plot(t, v_kph, color="C0", linewidth=1.8)
    axs[0].set_ylabel("Speed [km/h]")

    # 2) Losses: inverter & motor ------------------------------------------- #
    axs[1].plot(t, df["inv_loss_W"], label="Inverter", color="C1", linewidth=1.6)
    axs[1].plot(t, df["mot_loss_W"], label="Motor",    color="C2", linewidth=1.6)
    axs[1].fill_between(t, df["inv_loss_W"], alpha=0.15, color="C1")
    axs[1].fill_between(t, df["mot_loss_W"], alpha=0.15, color="C2")
    axs[1].set_ylabel("Losses [W]")
    axs[1].legend(loc="upper right", frameon=False)

    # 3) Efficiency ---------------------------------------------------------- #
    axs[2].plot(t, df["efficiency_pct"], color="C3", linewidth=1.6)
    axs[2].set_ylabel("Efficiency [%]")
    axs[2].set_ylim(0, 100)

    # 4) Junction temperature ------------------------------------------------ #
    axs[3].plot(t, df["Tj_C"], color="C4", linewidth=1.6)
    axs[3].set_ylabel("Tj [°C]")
    axs[3].set_xlabel("Time [s]")

    # ── Final layout tweaks ──────────────────────────────────────────────── #
    fig.align_ylabels(axs)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()


if __name__ == "__main__":
    main()
