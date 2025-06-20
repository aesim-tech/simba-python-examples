#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Préparation des données du cycle de conduite pour SIMBA.
- Lecture du profil vitesse (CSV)
- Calcul de l'accélération filtrée
- Calcul du couple roue, puis moteur
- Conversion de la vitesse véhicule en vitesse moteur (RPM)

Le DataFrame final est exporté en CSV et Pickle ; il pourra ensuite être
injecté dans une source PWL ou FromFile dans votre design Simba.
"""

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                        PARAMÈTRES (modifiable)                       ║
# ╚══════════════════════════════════════════════════════════════════════╝

# Fichier CSV d’entrée : doit contenir deux colonnes nommées TIME_S et SPEED_MPS
CSV_INPUT_PATH       = "class2-2-Medium.csv"

# Noms des colonnes attendues dans le CSV
COL_TIME_S           = "TIME_S"       # [s]
COL_SPEED_KPH        = "SPEED_KPH"    # [m/s]

# Pas de temps (pour vérification et création d’une grille régulière si besoin)
SAMPLING_TIME_S      = 1            # [s]

# Paramètres véhicule / chaîne de traction
VEHICLE_MASS_KG      = 1_500          # [kg]
WHEEL_RADIUS_M       = 0.30           # [m]
GEAR_RATIO           = 7.0            # Démultiplication totale (roue ← moteur)
DRIVELINE_EFF        = 0.97           # Rendement mécanique (≈ essieu + pont)

# Résistances roulage & aérodynamiques
CRR                  = 0.012          # Coeff. roulement (sans dimension)
AIR_DENSITY_KGPM3    = 1.225          # [kg/m³]
FRONTAL_AREA_M2      = 2.2            # [m²]
DRAG_COEFF           = 0.25           # Cx
ROAD_GRADE_PCT       = 0.0            # Pente (+ = montée) in %

# Paramètres filtre accélération (Savitzky-Golay)
SG_WINDOW            = 11             # Doit être impair ; adaptez à SAMPLING_TIME
SG_POLY              = 7

# Fichiers de sortie
CSV_OUTPUT_PATH      = "prepared_drive_cycle.csv"
PICKLE_OUTPUT_PATH   = "prepared_drive_cycle.pkl"

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                         IMPORTS & CONSTANTES                         ║
# ╚══════════════════════════════════════════════════════════════════════╝
import math
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import os

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                             FONCTIONS                                ║
# ╚══════════════════════════════════════════════════════════════════════╝
def load_and_resample(csv_path: str,
                      sampling_time: float,
                      col_t: str,
                      col_v: str) -> pd.DataFrame:
    """
    Lit le CSV et renvoie un DataFrame resamplé sur une grille régulière.

    Le CSV peut (a) déjà contenir un pas fixe, ou (b) être irrégulier ;
    dans ce dernier cas on interpole linéairement.
    """
    df_raw = pd.read_csv(csv_path, comment="#")
    if not {col_t, col_v}.issubset(df_raw.columns):
        raise ValueError(f"Le CSV doit contenir les colonnes {col_t} et {col_v}")
    df_raw = df_raw[[col_t, col_v]].dropna().sort_values(col_t)

    t_start = df_raw[col_t].iloc[0]
    # On force le temps de départ à 0 pour simplifier les calculs
    df_raw[col_t] -= t_start

    # Grille régulière
    t_end = df_raw[col_t].iloc[-1]
    time_grid = np.arange(0.0, t_end + sampling_time, sampling_time)

    v_interp_kph = np.interp(time_grid,
                         df_raw[col_t].to_numpy(),
                         df_raw[col_v].to_numpy())

    v_interp_mps = v_interp_kph / 3.6  # Convertit km/h → m/s

    df = pd.DataFrame({
        "time_s": time_grid,
        "speed_mps": v_interp_mps
    })
    return df


def compute_acceleration(speed: np.ndarray,
                         dt: float,
                         sg_window: int,
                         sg_poly: int) -> np.ndarray:
    """Dérive la vitesse puis applique un filtre de Savitzky-Golay."""
    # dérivée centrale => a_n = (v_{n+1} - v_{n-1}) / (2 dt)
    a_raw = np.gradient(speed, dt)

    # Filtrage SG pour limiter le bruit
    # (window doit être impair et <= len(speed))
    window = min(sg_window, len(speed) // 2 * 2 + 1)
    if window < sg_poly + 2:  # sécurité
        window = sg_poly + 2 | 1  # force impair
    a_filt = savgol_filter(a_raw, window_length=window, polyorder=sg_poly)
    return a_filt


def compute_longitudinal_force(v_mps: np.ndarray,
                               a_mps2: np.ndarray,
                               mass_kg: float,
                               crr: float,
                               rho: float,
                               area: float,
                               cd: float,
                               grade_pct: float) -> np.ndarray:
    """
    Calcul du besoin tractive roue (N) :

        F_total = m a + F_rr + F_aero + F_grade
    """
    g = 9.80665  # gravité
    F_inertia = mass_kg * a_mps2
    F_rr = mass_kg * g * crr * np.cos(np.arctan(grade_pct / 100.0))
    F_aero = 0.5 * rho * area * cd * v_mps**2
    F_grade = mass_kg * g * np.sin(np.arctan(grade_pct / 100.0))
    return F_inertia + F_rr + F_aero + F_grade


def vehicle_to_motor(speed_mps: np.ndarray,
                     force_N: np.ndarray,
                     wheel_r_m: float,
                     gear_ratio: float,
                     eta_mech: float) -> pd.DataFrame:
    """
    Convertit vitesse & force roue → vitesse & couple moteur.
    """
    # Vitesse roue rad/s
    omega_wheel_radps = speed_mps / wheel_r_m
    # Vitesse moteur rad/s puis RPM
    omega_motor_radps = omega_wheel_radps * gear_ratio
    rpm_motor = omega_motor_radps * 60.0 / (2.0 * math.pi)

    # Couple roue (N·m)
    torque_wheel_Nm = force_N * wheel_r_m
    # Couple moteur (en tenant compte du rendement mécanique global)
    torque_motor_Nm = torque_wheel_Nm / (gear_ratio * eta_mech)

    return pd.DataFrame({
        "motor_rpm": rpm_motor,
        "motor_torque_Nm": torque_motor_Nm
    })


# ╔══════════════════════════════════════════════════════════════════════╗
# ║                              MAIN                                    ║
# ╚══════════════════════════════════════════════════════════════════════╝
def main():
    # 1. Charge et resample le profil vitesse

    current_folder = os.path.dirname(os.path.abspath(__file__))
    csv_input_file = os.path.join(current_folder  , CSV_INPUT_PATH)

    df = load_and_resample(
        csv_input_file,
        SAMPLING_TIME_S,
        COL_TIME_S,
        COL_SPEED_KPH
    )

    # 2. Accélération filtrée
    df["acc_mps2"] = compute_acceleration(
        df["speed_mps"].to_numpy(),
        SAMPLING_TIME_S,
        SG_WINDOW,
        SG_POLY
    )

    # 3. Force longitudinale roue
    df["force_N"] = compute_longitudinal_force(
        v_mps=df["speed_mps"].to_numpy(),
        a_mps2=df["acc_mps2"].to_numpy(),
        mass_kg=VEHICLE_MASS_KG,
        crr=CRR,
        rho=AIR_DENSITY_KGPM3,
        area=FRONTAL_AREA_M2,
        cd=DRAG_COEFF,
        grade_pct=ROAD_GRADE_PCT
    )

    # 4. Conversion roue → moteur
    df_motor = vehicle_to_motor(
        speed_mps=df["speed_mps"].to_numpy(),
        force_N=df["force_N"].to_numpy(),
        wheel_r_m=WHEEL_RADIUS_M,
        gear_ratio=GEAR_RATIO,
        eta_mech=DRIVELINE_EFF
    )

    # 5. Fusion
    df_final = pd.concat([df, df_motor], axis=1)

    # 6. Export
    df_final.to_csv(os.path.join(current_folder  , CSV_OUTPUT_PATH), index=False)
    df_final.to_pickle(os.path.join(current_folder  , PICKLE_OUTPUT_PATH))

    print(f"✅  Cycle préparé : {len(df_final)} points exportés vers {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()