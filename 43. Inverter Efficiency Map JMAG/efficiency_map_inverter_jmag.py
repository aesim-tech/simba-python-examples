"""
Efficiency Map
"""

import numpy
import threading
import os
import math
import tqdm  # for the progress bar
from aesim.simba import ProjectRepository, License

#############################
#   SIMULATION PARAMETERS   #
#############################
number_of_parallel_simulations = License.NumberOfAvailableParallelSimulationLicense()  # SIMBA parallel licenses
case_temperature = 80           # Case temperature [Celsius]
Rg = 4.5                        # Gate resistance [Ohm]
switching_frequency = 50000     # Switching Frequency [Hz]
bus_voltage = 500.0            # Bus Voltage [V]
max_speed_ref = 4000            # RPM
max_current_ref = 100.0         # A

number_of_speed_points = 15     # Total sims = speed_points * current_points
number_of_current_points = 15   # Total sims = speed_points * current_points
relative_minimum_speed = 0.2    # fraction of max_speed_ref
relative_minimum_current = 0.2  # fraction of max_current_ref

# Get motor parameters from Simba file
current_folder = os.path.dirname(os.path.abspath(__file__))
project = ProjectRepository(os.path.join(current_folder, "efficiency_map_inverter_jmag.jsimba"))
simba_full_design = project.GetDesignByName('Design')
Ld_H = float(simba_full_design.Circuit.GetVariableValue("Ld"))
Lq_H = float(simba_full_design.Circuit.GetVariableValue("Lq"))
PM_Wb = float(simba_full_design.Circuit.GetVariableValue("Phi_mag"))
NPP = float(simba_full_design.Circuit.GetVariableValue("NPP"))

if os.environ.get("SIMBA_SCRIPT_TEST"):  # Accelerate simulation in test environment.
    number_of_speed_points = 2
    number_of_current_points = 2

# Threading primitives
semaphore = threading.Semaphore(number_of_parallel_simulations)  # throttle concurrent jobs
file_lock = threading.Lock()  # guard reading the .jsimba repository

#############################
#           METHODS         #
#############################
def run_simulation(id_ref, iq_ref, speed_ref, case_temperature, Rg, sim_number, results):
    """
    Run SIMBA Simulation of the design "Full Design" and place the results into 'results[sim_number]'.

    :param id_ref: d-axis current reference [A]
    :param iq_ref: q-axis current reference [A]
    :param speed_ref: Speed Reference [RPM]
    :param case_temperature: Case Temperature [Celsius]
    :param Rg: Gate Resistance [Ohm]
    :param sim_number: Simulation Number. Used as results index
    :param results: shared list (index-safe) used to store results
    """
    log = False  # if true, log simulation results

    # Respect SIMBA license concurrency
    with semaphore:
        # Read the jsimba file (guarded to avoid any race on repository load)
        with file_lock:
            local_project = ProjectRepository(os.path.join(current_folder, "efficiency_map_inverter_jmag.jsimba"))

        simba_full_design = local_project.GetDesignByName('Design')

        # Set Test Target Data
        # operating point
        simba_full_design.Circuit.SetVariableValue("RPM", str(speed_ref))
        simba_full_design.Circuit.GetDeviceByName("Id_ref").Value = str(id_ref)
        simba_full_design.Circuit.GetDeviceByName("Iq_ref").Value = str(iq_ref)

        # inverter settings
        simba_full_design.Circuit.SetVariableValue("Tcase", str(case_temperature))
        simba_full_design.Circuit.SetVariableValue("fpwm", str(switching_frequency))
        simba_full_design.Circuit.SetVariableValue("DC", str(bus_voltage))

        for i in range(1, 6):
            simba_full_design.Circuit.GetDeviceByName(f"T{i}").Rgon = Rg

        if log:
            print(f"\n{sim_number}> Running Full Model... (Id_ref={id_ref:.2f} A "
                  f"Iq_ref={iq_ref:.2f} A speed_ref={speed_ref:.2f} RPM)")

        # Run Simulation
        job = simba_full_design.TransientAnalysis.NewJob()
        status = job.Run()

        if str(status) != "OK":
            print(job.Summary()[:-1])
            return  # ERROR
        if log:
            print(job.Summary()[:-1])

        # Read and return results
        inverter_losses = job.GetSignalByName('Inverter_Losses - Heat Flow').DataPoints[-1]
        motor_losses = job.GetSignalByName('JmagRTMotor1 - Total Loss (average)').DataPoints[-1]
        actual_torque = job.GetSignalByName('JmagRTMotor1 - Te').DataPoints[-1]
        actual_speed_rpm = job.GetSignalByName('speed_rpm - Out').DataPoints[-1]
        input_power = job.GetSignalByName('Pin - P').DataPoints[-1]
        output_power = job.GetSignalByName('Pout - Out').DataPoints[-1]

        if actual_speed_rpm < 0:
            return  # ERROR

        total_losses = inverter_losses + motor_losses
        efficiency = 1 - total_losses / (total_losses + input_power)

        if log:
            print(f'{sim_number}> Efficiency = {100*efficiency:.2f}%  Input Power {input_power:.2f}W '
                  f'total_losses  {total_losses:.2f}W')

        # Store results at fixed index (thread-safe since each sim_number is unique)
        results[sim_number] = [inverter_losses, motor_losses, actual_torque,
                               actual_speed_rpm, efficiency, input_power, output_power]


def SelectIdIq(ref_idiq, current_ref, speed_ref):
    """
    Calculate Id and Iq references with MTPA and flux weakening.
    Returns True if success, False if this point is not achievable.
    """
    ret = False
    Vdc_V = bus_voltage
    Ia_A = current_ref
    speed_rpm = speed_ref

    Vo_V = Vdc_V / 2.0
    speed_radpsec = speed_rpm / 60 * 2 * math.pi

    Beta_MTPA_rad = 0.0
    if abs(Ld_H - Lq_H) > 1.0e-8:
        nume = -PM_Wb + math.sqrt(PM_Wb**2 + 8 * (Lq_H - Ld_H)**2 * Ia_A**2)
        deno = 4.0 * (Lq_H - Ld_H) * Ia_A
        Beta_MTPA_rad = math.asin(nume / deno)

    id_MTPA_A = -1.0 * Ia_A * math.sin(Beta_MTPA_rad)
    iq_MTPA_A = Ia_A * math.cos(Beta_MTPA_rad)

    Flux_Wb = math.sqrt((PM_Wb + Ld_H * id_MTPA_A) ** 2 + (Lq_H * iq_MTPA_A) ** 2)
    corner_speed_radpsec_mech = (Vo_V / Flux_Wb) / NPP
    speed_radpsec_elec = speed_radpsec * NPP

    if speed_radpsec < corner_speed_radpsec_mech:
        # MTPA (Mode 1)
        ref_idiq[0] = id_MTPA_A
        ref_idiq[1] = iq_MTPA_A
        ret = True
    else:
        # Flux weakening (Mode 2)
        iq_FW_A = iq_MTPA_A
        for _ in range(100):
            iq_A_old = iq_FW_A
            if (Vo_V / speed_radpsec_elec) ** 2 - (Lq_H * iq_FW_A) ** 2 < 0.0:
                continue

            id_FW_A = (-PM_Wb + math.sqrt((Vo_V / speed_radpsec_elec) ** 2 - (Lq_H * iq_FW_A) ** 2)) / Ld_H
            if Ia_A * Ia_A - id_FW_A * id_FW_A < 0.0:
                continue
            iq_FW_A = math.sqrt(Ia_A * Ia_A - id_FW_A * id_FW_A)
            if math.fabs(iq_FW_A - iq_A_old) < 1.0e-3:
                ref_idiq[0] = id_FW_A
                ref_idiq[1] = iq_FW_A
                ret = True
                break
    return ret


#############################
#         MAIN SCRIPT       #
#############################
if __name__ == "__main__":  # Called only in main thread.

    # 1) Update RTT path
    current_folder = os.path.dirname(os.path.abspath(__file__))
    path_RTT = os.path.join(current_folder, "100k_D_D_I-.rtt")

    project = ProjectRepository(os.path.join(current_folder, 'efficiency_map_inverter_jmag.jsimba'))
    design = project.GetDesignByName('Design')
    pmsm = design.Circuit.GetDeviceByName("JmagRTMotor1")
    pmsm.RttFilePath.UserValue = path_RTT
    project.Save()

    # 2) Initialization
    min_speed_ref = relative_minimum_speed * max_speed_ref
    min_current_ref = relative_minimum_current * max_current_ref

    speed_refs = numpy.arange(min_speed_ref, max_speed_ref,
                              (max_speed_ref - min_speed_ref) / number_of_speed_points)
    current_refs = numpy.arange(min_current_ref, max_current_ref,
                                (max_current_ref - min_current_ref) / number_of_current_points)

    # Build job list (pool_args) and pre-size results
    pool_args = []
    i = 0
    for current_ref in current_refs:
        for speed_ref in speed_refs:
            ref_idiq = [0.0, 0.0]
            if SelectIdIq(ref_idiq, current_ref, speed_ref):
                pool_args.append((ref_idiq[0], ref_idiq[1], speed_ref, case_temperature, Rg, i))
                i += 1

    results = [None] * len(pool_args)

    # 3) Create and start threads
    threads = []
    for args in pool_args:
        # append shared 'results' at the end of args for this thread
        t = threading.Thread(target=run_simulation, args=(*args, results))
        threads.append(t)
        t.start()

    # 4) Wait for completion with progress bar
    for t in tqdm.tqdm(threads, desc="Running simulations"):
        t.join()

    # 5) Collect and save results
    inverter_losses = []
    motor_losses = []
    input_power = []
    Pout = []
    t_arr = []
    s_arr = []
    e_arr = []

    for r in results:
        if r is None:
            continue  # skip failed runs
        inverter_losses.append(r[0])
        motor_losses.append(r[1])
        t_arr.append(r[2])
        s_arr.append(r[3])
        e_arr.append(r[4])
        input_power.append(r[5])
        Pout.append(r[6])

    inverter_losses = numpy.array(inverter_losses)
    motor_losses = numpy.array(motor_losses)
    input_power = numpy.array(input_power)
    Pout = numpy.array(Pout)
    t_arr = numpy.array(t_arr)
    s_arr = numpy.array(s_arr)
    e_arr = numpy.array(e_arr)

    results_dir = os.path.join(current_folder, "results")
    os.makedirs(results_dir, exist_ok=True)

    numpy.savetxt(os.path.join(results_dir, "inverter_losses.txt"), inverter_losses)
    numpy.savetxt(os.path.join(results_dir, "motor_losses.txt"), motor_losses)
    numpy.savetxt(os.path.join(results_dir, "input_power.txt"), input_power)
    numpy.savetxt(os.path.join(results_dir, "torque.txt"), t_arr)
    numpy.savetxt(os.path.join(results_dir, "speed.txt"), s_arr)
    numpy.savetxt(os.path.join(results_dir, "efficiency.txt"), e_arr)
    numpy.savetxt(os.path.join(results_dir, "Pout.txt"), Pout)