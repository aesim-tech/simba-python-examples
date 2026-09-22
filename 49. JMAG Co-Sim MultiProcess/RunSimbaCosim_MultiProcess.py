###########################################################
# SIMBA-JMAG co-simulation Parallel Run Sample
# Created by Powersys Inc.
# Copyright (C) 2026, Powersys Inc. All Rights Reserved.
###########################################################
from aesim.simba import License, ProjectRepository
from importlib.metadata import version, PackageNotFoundError
import os
import shutil
import logging
import logging.handlers
import multiprocessing
from datetime import datetime
import matplotlib.pyplot as plt
from tqdm import tqdm

# Get number of available SIMBA parallel licenses in this machine
number_of_SIMBA_parallel_licenses = License.NumberOfAvailableParallelSimulationLicense()  

###########################################################
############ User define parameters from here #############

# Flag for PSL license for JMAG
os.environ["JMAG_MULTI_CALCULATION"] = "1" # Set "1" to enable JMAG PSL license. Set "0" to disable it.

# Define JMAG install directory and design name in jsimba file
JMAG_install_directory = r"C:\\Program Files\\JMAG-Designer25.0"
input_jsimba = "Co-simulation_with_JMAG_FEA_Model.jsimba"
design_name = "JMAG-DirectCoupling_SVPWM" # input jsimba design name
input_jcf = "Co-simulation_with_JMAG_FEA_Model.jcf" # input jcf name
input_xml =  "Co-simulation_with_JMAG_FEA_Model_csl.xml" # input xml file

# Set number of simulations you want to run in parallel. It should be less than or equal to the number of available SIMBA parallel simulation licenses. 
num_parallel_simulations = 4 # You can replace this number to a parameter "number_of_SIMBA_parallel_licenses". This allows to run all available parallel simulations.

# Define sweep parameters 
subcycling_rates = [20] # [1,5] # For demonstration purpose, this scripts is shipped with only one subcycling rate, 20. You can replace this list with [1,5] to run a parametric run with 1 and 5 subcycling rates.
carrier_frequencies = [3300, 5000, 10000, 20000] # Parametric run with 3.3kHz, 5kHz, 10kHz and 20 kHz

# Set simulation time step and end time
time_step = 1e-6 # Unit seconds. 
end_time = 1e-4 # Unit seconds. For demonstration purpose, this scripts is shipped with a short simulation time, 1e-4 seconds. You can replace this number to a longer simulation time, e.g., 0.01 seconds.


############ User define parameters to here ###############
###########################################################


# Set up input simba file
def setup_inputs(subcycling_rates, carrier_frequencies, original_folder_abs, input_model_list):

     # For loops to setup input files
    for i in subcycling_rates:
        for j in carrier_frequencies:
            custom_logger(logging,"......")

            # To avoid overwriting output files while running multiple simulations in parallel, 
            # we create a new working folder for each simulation and copy input files (.jsimba, .jcf and .xml) from the original folder.
            # If the folder already exists, do nothing. 
            # https://www.geeksforgeeks.org/copy-all-files-from-one-directory-to-another-using-python/
            test_folder = "test_N=" + str(i) + "_CarrierFreq="+str(j)+"Hz"
            test_folder_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), test_folder)
            custom_logger(logging,"..." + test_folder)

            if not os.path.exists(test_folder):
                custom_logger(logging,"...Create a folder:" + test_folder)
                shutil.copytree(original_folder_abs, test_folder_abs)
            else:
                custom_logger(logging,"...Already exists")


            #%%  Open Design
            filepath = os.path.join(test_folder_abs, input_jsimba)
            project = ProjectRepository(filepath) # Open file
            custom_logger(logging,"...Open simba file")


            # Set simulation parameters
            design = project.GetDesignByName(design_name)
            JMAGblock = design.Circuit.GetDeviceByName('M1')
            JMAGblock.InputFilePath.UserValue  = os.path.join(test_folder_abs  ,  input_jcf)
            JMAGblock.XmlFilePath.UserValue  = os.path.join(test_folder_abs, input_xml)
            dllpath = JMAG_install_directory + r"\\Solver\\mod\\mag\\mod\\jbdll.dll" 
            JMAGblock.DllPath.UserValue  = dllpath 
            JMAGblock.SubcyclingRate = i
            for scope in JMAGblock.Scopes:
                    scope.Enabled = True
            design.Circuit.SetVariableValue("fpwm", str(j))

            design.TransientAnalysis.TimeStep = time_step
            design.TransientAnalysis.EndTime = end_time

            project.Save()
            custom_logger(logging,"...Simba file update, done")
            input_model_list.append(filepath)
            custom_logger(logging,"...New task was added to the list:"+filepath)

# Initialize worker process for logging
def init_worker(logging_queue):
    """
    Runs automatically when each worker process starts.
    Configures the worker to redirect all logs to the shared queue.
    """
    # Create a QueueHandler pointing to our shared logging queue
    queue_handler = logging.handlers.QueueHandler(logging_queue)

    # Configure the root logger inside this specific worker process
    worker_logger = logging.getLogger()
    worker_logger.setLevel(logging.INFO)

    # Clear any inherited handlers to prevent duplicate logging
    worker_logger.handlers = []
    worker_logger.addHandler(queue_handler)

# Run simulation
def run_simulation(filepath):
    # Log messages from this worker will be sent to the main process via the queue
    worker_logger = logging.getLogger()
    custom_logger(worker_logger,"==============================================")
    custom_logger(worker_logger,"...Run simba-jmag direct coupling model:" + filepath)

    # Open file
    project = ProjectRepository(filepath)

    # create a new job and run the simulation
    design = project.GetDesignByName(design_name)
    job = design.TransientAnalysis.NewJob()
    status = job.Run()
    custom_logger(worker_logger,job.Summary())

    # Check the status of the simulation
    if str(status) != "OK":
        custom_logger(worker_logger, "...Error occurred while running simulation:"+filepath)
        custom_logger(worker_logger,"==============================================")

        return  # ERROR
    else:
        custom_logger(worker_logger, "...Simulation completed successfully:"+filepath)

    # Extract results
    Iaout = job.GetSignalByName('CP1 - Current')
    Ibout = job.GetSignalByName('CP2 - Current')
    Icout = job.GetSignalByName('CP3 - Current')
    Tout = job.GetSignalByName('M1 - Te0')

    # Create and export results into csv file
    test_folder_abs = os.path.dirname(filepath)

    simba_result_file_abs = os.path.join(test_folder_abs, 'simba_current.csv')
    with open(simba_result_file_abs, 'w') as file:
        for t,Ia, Ib, Ic in zip(Iaout.TimePoints,Iaout.DataPoints, Ibout.DataPoints, Icout.DataPoints):
            file.write(f"{t:20.20f},{Ia:20.20f}, {Ib:20.20f}, {Ic:20.20f}"+"\n")
    custom_logger(worker_logger, "...Result csv exported:"+simba_result_file_abs)

    simba_result_file_abs = os.path.join(test_folder_abs, 'simba_torque.csv')
    with open(simba_result_file_abs, 'w') as file:
        for t,Te in zip(Tout.TimePoints,Tout.DataPoints):
            file.write(f"{t:20.20f},{Te:20.20f}"+"\n")
    custom_logger(worker_logger, "...Result csv exported:"+simba_result_file_abs)

    #%% Plot Curve
    plt.figure(1)
    try:
        plt.title('JMAG Co-simulation Current')
        plt.ylabel('Current (A)')
        plt.xlabel('time (s)')
        plt.plot(Iaout.TimePoints,Iaout.DataPoints, label = "Ia")
        plt.plot(Ibout.TimePoints,Ibout.DataPoints, label = "Ib")
        plt.plot(Icout.TimePoints,Icout.DataPoints, label = "Ic")
        plt.legend() 
        plt.grid()
        simba_result_image_abs = os.path.join(test_folder_abs, 'simba_current.png')
        plt.savefig(simba_result_image_abs, dpi=300, bbox_inches='tight')
        custom_logger(worker_logger, "...Result graph created:"+simba_result_image_abs)
    finally:
        plt.close(1)

    plt.figure(2)
    try:
        plt.title('JMAG Co-simulation Torque')
        plt.ylabel('Torque (Nm)')
        plt.xlabel('time (s)')
        plt.plot(Tout.TimePoints,Tout.DataPoints)
        plt.grid()
        simba_result_image_abs = os.path.join(test_folder_abs, 'simba_torque.png')
        plt.savefig(simba_result_image_abs, dpi=300, bbox_inches='tight')
        custom_logger(worker_logger, "...Result graph created:"+simba_result_image_abs)
    finally:
        plt.close(2)

    custom_logger(worker_logger,"==============================================")
        

# A function for log
def custom_logger(logging, message):
	logging.info(message)
	#print(message)

if __name__ == "__main__":
    manager = None
    listener = None
    file_handler = None
    listener_started = False

    try:    
        # 1. Create a process-safe Queue via Manager
        # (Standard multiprocessing.Queue() can fail or hang during Pool initialization)
        manager = multiprocessing.Manager()
        queue = manager.Queue()

        # 2. Configure the main handler/formatter for the output destination
        console_handler = logging.StreamHandler()
        path = os.path.dirname(os.path.abspath(__file__))
        logfilename= "simba-jmag_pmsm_"+datetime.now().strftime("%m%d%H%M%S%f")+".log"
        file_handler = logging.FileHandler(os.path.join(path, logfilename), mode="w")

        formatter = logging.Formatter('%(asctime)s | %(processName)s | %(levelname)s | %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # 3. Create and start the QueueListener in the main process
        listener = logging.handlers.QueueListener(queue, console_handler, file_handler, respect_handler_level=True)
        listener.start()
        listener_started = True

        # 4. Create a QueueHandler pointing to our shared logging queue
        queue_handler = logging.handlers.QueueHandler(queue)
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers = []
        root_logger.addHandler(queue_handler)

        # 5. Write environment variables and input parameters to log file
        custom_logger(root_logger, "###### SIMBA-JMAG co-simulation Parallel Run Sample (Multi-proccess) #####")
        custom_logger(root_logger, "###### Created by Powersys Inc. #####")
        custom_logger(root_logger, "###### Copyright (C) 2026, Powersys Inc. All Rights Reserved. #####")

        custom_logger(root_logger, "Number of available SIMBA parallel simulation licenses: " + str(number_of_SIMBA_parallel_licenses))
        custom_logger(root_logger, "Environment VariableJMAG_MULTI_CALCULATION: " + os.environ.get("JMAG_MULTI_CALCULATION"))
        custom_logger(root_logger, "JMAG Install Directory: " + JMAG_install_directory)
        custom_logger(root_logger, "Input .jsimba file: " + input_jsimba)
        custom_logger(root_logger, "Design name: " + design_name)
        custom_logger(root_logger, "Input .jcf file: " + input_jcf)
        custom_logger(root_logger, "XML file: " + input_xml)
        custom_logger(root_logger, "SIMBA version: " + version('aesim.simba'))


        # 6. Define original input file folder
        original_folder = "original"
        original_folder_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), original_folder)
        jmag_result_file = "Co-simulation_with_JMAG_FEA_Model.jplot"

        # 7. Create input models using specified sweep parameters
        input_model_list = []
        setup_inputs(subcycling_rates, carrier_frequencies, original_folder_abs, input_model_list)

        # 8. Split the input_model_list into sublists for each process
        sublists = [input_model_list[i : i + num_parallel_simulations] for i in range(0, len(input_model_list), num_parallel_simulations)]
                    # Result:
                    # When there is 3 available SIMBA parallel simulation licenses and 10 input models, the sublists will be: 
                    # [[Model1, Model2, Model3], [Model4, Model5, Model6], [Model7, Model8, Model9], [Model10]]

        # 9. Loop through each sublist and run them in parallel
        # Inside of the loop, spin up the Multiprocessing Pool
        # We use 'initializer' to pass the queue to each worker as it spawns
        for sublist in sublists:
            custom_logger(root_logger, f"Starting a batch of {len(sublist)} simulations in parallel...") 

            with multiprocessing.Pool(
                processes=num_parallel_simulations, initializer=init_worker, initargs=(queue,)
            ) as pool:
                results = list(tqdm(
                    pool.imap_unordered(run_simulation, sublist), 
                    total=len(sublist),
                    desc="Processing items"
                ))
                custom_logger(root_logger, f"Finished a batch of {len(sublist)} simulations in parallel...")         

            custom_logger(root_logger, "... End test")

                
    finally:
        # 10. Stop the listener after all workers finish and Clean up the manager and its resources
        try:
            if listener and listener_started:
                listener.stop()
        finally:
            try:
                if file_handler:
                    file_handler.close()
            finally:
                if manager:
                    manager.shutdown()  
