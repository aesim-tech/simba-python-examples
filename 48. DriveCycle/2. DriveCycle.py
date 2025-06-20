#!/usr/bin/env python
"""
Run one SIMBA transient (1 s) per operating point of a drive-cycle, passing the
junction temperature from each run to the next.  Results are saved as a Pandas
DataFrame in drive_cycle_results.pkl.

Prerequisites
-------------
* aesim-simba Python package with a valid licence
* drive_cycle_inverter_jmag.jsimba located alongside this script
* prepared_drive_cycle.pkl (produced by your pre-processing pipeline) containing
  the columns:
      time_s, speed_mps, acc_mps2, force_N,
      motor_rpm, motor_torque_Nm
"""

import os, math, pandas as pd, numpy as np
from datetime import datetime
from aesim.simba import ProjectRepository, License

###############################################################################
# User-tunable constants (copied from your efficiency-map example)
###############################################################################
CASE_TEMPERATURE_C   = 80.0     # [°C]
BUS_VOLTAGE_V        = 500.0    # [V]
SWITCHING_FREQ_HZ    = 50_000   # [Hz]
GATE_RESISTANCE_OHM  = 4.5      # [Ω]

# Device / variable names inside the jsimba design ---------------------------
RPM_VAR              = "RPM"        # Circuit variable for mechanical speed
ID_REF_NODE          = "Id_ref"     # Device providing Id reference
IQ_REF_NODE          = "Iq_ref"     # Device providing Iq reference
TJ_INIT_VAR          = "TJ_init"    # *scalar variable* used to feed initial
                                    # junction temp
# Signal names to record --------------------------------------------
SIG_INV_LOSS   = 'Inverter_Losses - Heat Flow'
SIG_MOTOR_LOSS = 'JmagRTMotor1 - Total Loss (average)'
SIG_PIN        = 'Pin - P'
SIG_POUT       = 'Pout - Out'
SIG_TJ_MAX     = 'T1 - Junction Temperature (°)'   # adapt to your design if different
SIG_TE         = 'JmagRTMotor1 - Te'  # actual torque
SIG_SPEED_RPM  = 'speed_rpm - Out'    # actual mechanical speed
###############################################################################

RPM_EPS = 1e-3 # treat any |RPM| below this as “stand-still”

HERE = os.path.abspath(os.path.dirname(__file__))
JSIMBA_PATH = os.path.join(HERE, "drive_cycle_inverter_jmag.jsimba")
CYCLE_PATH  = os.path.join(HERE, "prepared_drive_cycle.csv")
OUT_PKL     = os.path.join(HERE, "drive_cycle_results.pkl")

###############################################################################
#   Helper – MTPA + flux-weakening Id/Iq calculator (unchanged from your code)
###############################################################################
def select_id_iq(current_a: float, speed_rpm: float, *, Vdc_V=BUS_VOLTAGE_V,
                 Ld_H=0.0, Lq_H=0.0, Phi_Wb=0.0, NPP=0):
    """
    Returns (Id_A, Iq_A) or (None, None) if the point is infeasible.
    """
    Ia_A = current_a
    Vo_V = Vdc_V / 2.0
    ω_m  = speed_rpm * 2*math.pi / 60.0       # mech rad/s
    ω_e  = ω_m * NPP                          # elec rad/s

    # --- MTPA ---------------------------------------------------------------
    if abs(Ld_H - Lq_H) < 1e-9:
        β_rad = 0.0
    else:
        nume = -Phi_Wb + math.sqrt(Phi_Wb**2 +
                                   8*(Lq_H - Ld_H)**2 * Ia_A**2)
        deno = 4.0*(Lq_H - Ld_H)*Ia_A
        β_rad = math.asin(nume / deno)
    Id_MTPA = -Ia_A * math.sin(β_rad)
    Iq_MTPA =  Ia_A * math.cos(β_rad)

    # flux / speed limit -----------------------------------------------------
    ψ = math.hypot(Phi_Wb + Ld_H*Id_MTPA, Lq_H*Iq_MTPA)
    ω_m_corner = (Vo_V / ψ) / NPP       # mech rad/s

    if ω_m < ω_m_corner + 1e-6:         # inside MTPA operating zone
        return Id_MTPA, Iq_MTPA

    # flux-weakening iteration ----------------------------------------------
    Iq_FW = Iq_MTPA
    for _ in range(100):
        Id_old, Iq_old = None, Iq_FW
        # voltage limit
        term = Vo_V/ω_e
        if term**2 - (Lq_H*Iq_FW)**2 < 0:        # infeasible
            break
        Id_FW = (-Phi_Wb + math.sqrt(term**2 - (Lq_H*Iq_FW)**2)) / Ld_H
        # current magnitude limit
        if Ia_A**2 - Id_FW**2 < 0:
            break
        Iq_FW = math.sqrt(Ia_A**2 - Id_FW**2)
        if abs(Iq_FW - Iq_old) < 1e-3:
            return Id_FW, Iq_FW
    return None, None

###############################################################################
#                                MAIN RUN                                    #
###############################################################################
def main():
    # ------------------------------------------------------------------ data
    cycle = pd.read_csv(CYCLE_PATH)
    print(f"Loaded drive-cycle with {len(cycle)} points.")

    # ---------------------------------------------------------------- SIMBA
    project = ProjectRepository(JSIMBA_PATH)
    design  = project.GetDesignByName("Design")

    # cache motor params used by select_id_iq -------------------------------
    Ld_H   = float(design.Circuit.GetVariableValue("Ld"))
    Lq_H   = float(design.Circuit.GetVariableValue("Lq"))
    Phi_Wb = float(design.Circuit.GetVariableValue("Phi_mag"))
    NPP    = int  (design.Circuit.GetVariableValue("NPP"))

    results = []

    tj_prev = 25.0  # °C – initial junction temperature
    for idx, row in cycle.iterrows():
        rpm    = row["motor_rpm"]
        torque = row["motor_torque_Nm"]

        # ───────────────────────────────────────────────────────────────────────
        # Special case: stand-still  ►  no switching, no copper loss (assumption)
        # ───────────────────────────────────────────────────────────────────────
        if abs(rpm) < RPM_EPS:
            results.append({
                "time_s"              : row["time_s"],
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
                "Tj_C"                : tj_prev,      # unchanged
                "actual_torque_Nm"    : 0.0,
                "actual_speed_rpm"    : 0.0,
            })
            print(f"[{idx:>4}/{len(cycle)}]  RPM=0  — skipped (Tj={tj_prev:.1f} °C)")
            continue
        # ───────────────────────────────────────────────────────────────────────

        # approximate phase current magnitude from torque via kt
        kt = 1.0                           # [Nm/A] – replace by your machine's
        Ia = abs(torque / kt)

        Id, Iq = select_id_iq(Ia, rpm,
                              Vdc_V=BUS_VOLTAGE_V,
                              Ld_H=Ld_H, Lq_H=Lq_H,
                              Phi_Wb=Phi_Wb, NPP=NPP)
        if Id is None:
            print(f"⚠️  Point {idx}: infeasible – skipped.")
            continue

        # ---------------------- set operating point & inverter settings ----
        design.Circuit.SetVariableValue(RPM_VAR, str(rpm))
        design.Circuit.GetDeviceByName(ID_REF_NODE).Value = str(Id)
        design.Circuit.GetDeviceByName(IQ_REF_NODE).Value = str(Iq)

        # thermal & power-stage params
        design.Circuit.SetVariableValue("Tcase", str(CASE_TEMPERATURE_C))
        design.Circuit.SetVariableValue("fpwm",  str(SWITCHING_FREQ_HZ))
        design.Circuit.SetVariableValue("DC",    str(BUS_VOLTAGE_V))
        # hand over previous Tj
        design.Circuit.SetVariableValue(TJ_INIT_VAR, str(tj_prev))

        # optional: gate resistance
        for i in range(1, 6):
            try:
                design.Circuit.GetDeviceByName(f"T{i}").Rgon = GATE_RESISTANCE_OHM
            except AttributeError:
                pass  # skip if your design has fewer switches

        # ------------------------------- run transient (1 s) --------------
        job   = design.TransientAnalysis.NewJob()
        if str(job.Run()) != "OK":
            print(f"❌ Simulation {idx} failed:\n{job.Summary()}")
            continue

        # extract signals – last datapoint gives quasi-steady values -------
        inv_loss   = job.GetSignalByName(SIG_INV_LOSS).DataPoints[-1]      # W
        mot_loss   = job.GetSignalByName(SIG_MOTOR_LOSS).DataPoints[-1]    # W
        pin        = job.GetSignalByName(SIG_PIN).DataPoints[-1]           # W
        pout       = job.GetSignalByName(SIG_POUT).DataPoints[-1]          # W
        tj_prev    = job.GetSignalByName(SIG_TJ_MAX).DataPoints[-1]        # °C
        act_torque = job.GetSignalByName(SIG_TE).DataPoints[-1]
        act_speed  = job.GetSignalByName(SIG_SPEED_RPM).DataPoints[-1]

        total_loss = inv_loss + mot_loss
        eff        = 100.0 * pout / (pout + total_loss) if (pout + total_loss) else np.nan

        results.append({
            "time_s"              : row["time_s"],
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
            "Tj_C"                : tj_prev,
            "actual_torque_Nm"    : act_torque,
            "actual_speed_rpm"    : act_speed,
        })

        print(f"[{idx:>4}/{len(cycle)}]  "
              f"RPM={rpm:6.0f}  Tq={torque:6.1f} Nm  "
              f"η={eff:5.1f}%  Tj={tj_prev:5.1f} °C")

    # ----------------------------------- save all --------------------------
    df = pd.DataFrame(results)
    df.to_pickle(OUT_PKL)
    print(f"\n✅  Saved {len(df)} points to {OUT_PKL}")

if __name__ == "__main__":
    main()