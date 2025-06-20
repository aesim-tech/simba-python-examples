#!/usr/bin/env python
"""
Run SIMBA drive-cycle operating points **in parallel** (like the efficiency-map
example) while cascading junction temperature (Tj).

For every operating point we launch a separate SIMBA transient (1 s).  Before a
job is submitted we initialise **TJ_init** with *the most recent junction
temperature already returned by any completed job*.  That gives a reasonable
approximation of the evolving device temperature without enforcing strict
sequential execution, so we gain speed-up while still propagating thermal
history.

A tqdm progress-bar shows overall progress.

Notes
-----
* Requires the *tqdm* package (`pip install tqdm`).
* Each worker opens its own ProjectRepository instance – this is necessary
  because the SIMBA objects are not picklable across processes.
* The script uses `concurrent.futures.ProcessPoolExecutor`; adjust
  `max_workers` if you want to limit CPU usage.

"""

import os
import math
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager
from tqdm import tqdm

from aesim.simba import ProjectRepository, License

###############################################################################
# User-tunable constants (identical to original script)                       #
###############################################################################
CASE_TEMPERATURE_C   = 80.0     # [°C]
BUS_VOLTAGE_V        = 500.0    # [V]
SWITCHING_FREQ_HZ    = 50_000   # [Hz]
GATE_RESISTANCE_OHM  = 4.5      # [Ω]

# Device / variable names inside the jsimba design ---------------------------
RPM_VAR              = "RPM"        # Circuit variable for mechanical speed
ID_REF_NODE          = "Id_ref"     # Device providing Id reference
IQ_REF_NODE          = "Iq_ref"     # Device providing Iq reference
TJ_INIT_VAR          = "TJ_init"    # scalar variable used to feed initial Tj

# Signal names to record ------------------------------------------------------
SIG_INV_LOSS   = "Inverter_Losses - Heat Flow"
SIG_MOTOR_LOSS = "JmagRTMotor1 - Total Loss (average)"
SIG_PIN        = "Pin - P"
SIG_POUT       = "Pout - Out"
SIG_TJ_MAX     = "T1 - Junction Temperature (°)"   # adapt if different
SIG_TE         = "JmagRTMotor1 - Te"               # actual torque
SIG_SPEED_RPM  = "speed_rpm - Out"                 # actual mechanical speed
###############################################################################

RPM_EPS = 1e-3  # treat any |RPM| below this as stand-still

HERE = os.path.abspath(os.path.dirname(__file__))
JSIMBA_PATH = os.path.join(HERE, "drive_cycle_inverter_jmag.jsimba")
CYCLE_PATH  = os.path.join(HERE, "prepared_drive_cycle.csv")
OUT_PKL     = os.path.join(HERE, "drive_cycle_results.pkl")

###############################################################################
# Helper – MTPA + flux-weakening Id/Iq calculator (unchanged)                 #
###############################################################################

def select_id_iq(current_a: float, speed_rpm: float, *, Vdc_V=BUS_VOLTAGE_V,
                 Ld_H=0.0, Lq_H=0.0, Phi_Wb=0.0, NPP=0):
    """Return (Id_A, Iq_A) or (None, None) if the point is infeasible."""
    Ia_A = current_a
    Vo_V = Vdc_V / 2.0
    ω_m  = speed_rpm * 2*math.pi / 60.0       # mech rad/s
    ω_e  = ω_m * NPP                          # elec rad/s

    # --- MTPA -------------------------------------------------------------
    if abs(Ld_H - Lq_H) < 1e-9:
        β_rad = 0.0
    else:
        nume = -Phi_Wb + math.sqrt(Phi_Wb**2 +
                                   8*(Lq_H - Ld_H)**2 * Ia_A**2)
        deno = 4.0*(Lq_H - Ld_H)*Ia_A
        β_rad = math.asin(nume / deno)
    Id_MTPA = -Ia_A * math.sin(β_rad)
    Iq_MTPA =  Ia_A * math.cos(β_rad)

    # Flux / speed limit ---------------------------------------------------
    ψ = math.hypot(Phi_Wb + Ld_H*Id_MTPA, Lq_H*Iq_MTPA)
    ω_m_corner = (Vo_V / ψ) / NPP       # mech rad/s

    if ω_m < ω_m_corner + 1e-6:         # inside MTPA zone
        return Id_MTPA, Iq_MTPA

    # Flux-weakening iteration --------------------------------------------
    Iq_FW = Iq_MTPA
    for _ in range(100):
        Id_old, Iq_old = None, Iq_FW
        term = Vo_V/ω_e
        if term**2 - (Lq_H*Iq_FW)**2 < 0:        # infeasible
            break
        Id_FW = (-Phi_Wb + math.sqrt(term**2 - (Lq_H*Iq_FW)**2)) / Ld_H
        if Ia_A**2 - Id_FW**2 < 0:               # current limit hit
            break
        Iq_FW = math.sqrt(Ia_A**2 - Id_FW**2)
        if abs(Iq_FW - Iq_old) < 1e-3:
            return Id_FW, Iq_FW
    return None, None

###############################################################################
# Worker – executed in *individual* processes                                 #
###############################################################################

def simulate_point(idx: int, row_dict: dict, tj_init: float) -> tuple[int, dict]:
    """Simulate a single operating point and return (idx, result-dict)."""

    # Re-open project inside the worker (SIMBA objects are not picklable)
    project = ProjectRepository(JSIMBA_PATH)
    design  = project.GetDesignByName("Design")

    # Cache motor params – values are constant, so no performance concern
    Ld_H   = float(design.Circuit.GetVariableValue("Ld"))
    Lq_H   = float(design.Circuit.GetVariableValue("Lq"))
    Phi_Wb = float(design.Circuit.GetVariableValue("Phi_mag"))
    NPP    = int  (design.Circuit.GetVariableValue("NPP"))

    rpm    = row_dict["motor_rpm"]
    torque = row_dict["motor_torque_Nm"]

    # Stand-still shortcut
    if abs(rpm) < RPM_EPS:
        return idx, {
            "time_s"              : row_dict["time_s"],
            "motor_rpm_cmd"       : rpm,
            "motor_torque_cmd_Nm" : torque,
            "Id_A"                : 0.0,
            "Iq_A"                : 0.0,
            "inv_loss_W"          : 0.0,
            "mot_loss_W"          : 0.0,
            "total_loss_W"        : 0.0,
            "input_power_W"       : 0.0,
            "output_power_W"      : 0.0,
            "efficiency_pct"      : np.nan,
            "Tj_C"                : tj_init,
            "actual_torque_Nm"    : 0.0,
            "actual_speed_rpm"    : 0.0,
        }

    # Approximate phase current magnitude from torque via kt
    kt = 0.6  # [Nm/A]
    Ia = abs(torque / kt)

    Id, Iq = select_id_iq(Ia, rpm,
                          Vdc_V=BUS_VOLTAGE_V,
                          Ld_H=Ld_H, Lq_H=Lq_H,
                          Phi_Wb=Phi_Wb, NPP=NPP)
    if Id is None:   # infeasible point
        return idx, None

    # Configure operating point -------------------------------------------
    design.Circuit.SetVariableValue(RPM_VAR, str(rpm))
    design.Circuit.GetDeviceByName(ID_REF_NODE).Value = str(Id)
    design.Circuit.GetDeviceByName(IQ_REF_NODE).Value = str(Iq)

    # Thermal & power-stage params
    design.Circuit.SetVariableValue("Tcase", str(CASE_TEMPERATURE_C))
    design.Circuit.SetVariableValue("fpwm",  str(SWITCHING_FREQ_HZ))
    design.Circuit.SetVariableValue("DC",    str(BUS_VOLTAGE_V))
    design.Circuit.SetVariableValue(TJ_INIT_VAR, str(tj_init))

    # Optional: gate resistance
    for i in range(1, 7):
        try:
            design.Circuit.GetDeviceByName(f"T{i}").Rgon = GATE_RESISTANCE_OHM
        except AttributeError:
            pass

    # Run transient -------------------------------------------------------
    job = design.TransientAnalysis.NewJob()
    if str(job.Run()) != "OK":
        return idx, None

    # Extract quasi-steady datapoints (last)
    inv_loss   = job.GetSignalByName(SIG_INV_LOSS).DataPoints[-1]
    mot_loss   = job.GetSignalByName(SIG_MOTOR_LOSS).DataPoints[-1]
    pin        = job.GetSignalByName(SIG_PIN).DataPoints[-1]
    pout       = job.GetSignalByName(SIG_POUT).DataPoints[-1]
    tj_out     = job.GetSignalByName(SIG_TJ_MAX).DataPoints[-1]
    act_torque = job.GetSignalByName(SIG_TE).DataPoints[-1]
    act_speed  = job.GetSignalByName(SIG_SPEED_RPM).DataPoints[-1]

    total_loss = inv_loss + mot_loss

        # --- Efficiency (handles motoring & regen) -------------------------------
    if abs(pout) < 1e-3 and total_loss < 1e-3:
        eff = np.nan                          # completely idle → undefined
    else:
        eff = abs(pout) / (abs(pout) + total_loss)  # 0…1

        eff = eff * 100 #pct
    return idx, {
        "time_s"              : row_dict["time_s"],
        "motor_rpm_cmd"       : rpm,
        "motor_torque_cmd_Nm" : torque,
        "Id_A"                : Id,
        "Iq_A"                : Iq,
        "inv_loss_W"          : inv_loss,
        "mot_loss_W"          : mot_loss,
        "total_loss_W"        : total_loss,
        "input_power_W"       : pin,
        "output_power_W"      : pout,
        "efficiency_pct"      : eff,
        "Tj_C"                : tj_out,
        "actual_torque_Nm"    : act_torque,
        "actual_speed_rpm"    : act_speed,
    }

###############################################################################
# Main – orchestrates the parallel execution                                   #
###############################################################################

def main():
    cycle = pd.read_csv(CYCLE_PATH)
    n_points = len(cycle)
    print(f"Loaded drive-cycle with {n_points} points.")

    # Shared state for latest junction temperature — via Manager Namespace
    manager = Manager()
    state   = manager.Namespace()
    state.latest_tj = 25.0  # initial value

    results = [None] * n_points  # pre-allocate list for random arrival order

    max_workers = License.NumberOfAvailableParallelSimulationLicense()
    with ProcessPoolExecutor(max_workers=max_workers) as pool, tqdm(total=n_points) as pbar:
        futures = {}
        submit_idx = 0

        # Helper to submit next job
        def submit_job(i):
            row_dict = cycle.iloc[i].to_dict()
            fut = pool.submit(simulate_point, i, row_dict, state.latest_tj)
            futures[fut] = i

        # Prime the queue --------------------------------------------------
        for _ in range(min(max_workers, n_points)):
            submit_job(submit_idx)
            submit_idx += 1

        # Drain queue, keep submitting until done -------------------------
        while futures:
            for fut in as_completed(list(futures.keys())):
                idx = futures.pop(fut)
                idx_ret, res = fut.result()
                if res is not None:
                    results[idx_ret] = res
                    state.latest_tj = res["Tj_C"]  # UPDATE with *latest* Tj
                else:
                    print(f"⚠️  Point {idx} failed or infeasible – skipped.")
                pbar.update(1)

                if submit_idx < n_points:
                    submit_job(submit_idx)
                    submit_idx += 1

    # Convert list → DataFrame, dropping None entries
    df = pd.DataFrame([r for r in results if r is not None])
    df.to_pickle(OUT_PKL)
    print(f"\n✅  Saved {len(df)} points to {OUT_PKL}")

if __name__ == "__main__":
    main()
