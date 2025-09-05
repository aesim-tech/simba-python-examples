# test_script_execution.py
# Run all the scripts
import os
import subprocess
import pytest
import nbformat
import sys
import time
from nbconvert.preprocessors import ExecutePreprocessor, CellExecutionError

# --------------------------------------------------------------------------------------
# INTERNAL SCRIPT FOR SIMBA TEAM
# --------------------------------------------------------------------------------------
# Purpose:
# This script is developed for internal use by the SIMBA team. It's primary function is
# to ensure that all tests and notebooks work as expected before any new release.
# --------------------------------------------------------------------------------------

def get_python_command():
    if sys.platform.startswith('win'):
        return 'python'  # On Windows, the command is typically 'python'
    elif sys.platform.startswith('darwin'):
        return 'python3' # On macOS (Darwin), the command is typically 'python3'
    elif sys.platform.startswith('linux'):
        return 'python3' # On Linux, the command is also typically 'python3'
    else:
        return 'python'  # Default to 'python' if the platform is not recognized


def run_python_script(path):
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env["SIMBA_SCRIPT_TEST"] = "True"
    python_command = get_python_command()

    start_time = time.time()
    try:
        result = subprocess.check_output([python_command, path], stderr=subprocess.STDOUT, universal_newlines=True, env=env)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"[OK] {os.path.basename(path)} executed successfully in {execution_time:.2f}s")
        return result
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"[FAIL] {os.path.basename(path)} failed after {execution_time:.2f}s")
        print("--- Script output ---")
        if e.output:
            print(e.output)
        else:
            print("No output captured")
        print("--- End script output ---")
        raise

def run_jupyter_notebook(path):
    original_cwd = os.getcwd()  # Save the original current working directory
    notebook_dir = os.path.dirname(path)  # Get the notebook's directory

    start_time = time.time()
    try:
        os.chdir(notebook_dir)  # Change to the notebook's directory

        with open(path, encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
            ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

            try:
                ep.preprocess(nb, {'metadata': {'path': notebook_dir}})
                end_time = time.time()
                execution_time = end_time - start_time
                print(f"[OK] {os.path.basename(path)} executed successfully in {execution_time:.2f}s")
            except CellExecutionError as e:
                end_time = time.time()
                execution_time = end_time - start_time
                print(f"[FAIL] {os.path.basename(path)} failed after {execution_time:.2f}s")
                print(f"Error executing {os.path.basename(path)}: {e}")
                raise

    finally:
        os.chdir(original_cwd)  # Revert back to the original directory

def run_tests_in_folder(folder_path):

    if ('JMAG' in folder_path or '44. Modulation Strategies Motor Drive' in folder_path) and not sys.platform.startswith('win'):
        print(f"[SKIP]  Skipping {os.path.basename(folder_path)} (JMAG only works on Windows)")
        return # JMAG works only on windows

    folder_name = os.path.basename(folder_path)
    print(f"\n[FOLDER] Testing folder: {folder_name}")

    script_count = 0
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if file.endswith(".py"):
            if file =="DistributionPV.py" or file.endswith("plot.py"): # Skip UI and plot scripts
                continue
            script_count += 1
            run_python_script(full_path)
        elif file.endswith(".ipynb"):
            script_count += 1
            run_jupyter_notebook(full_path)

    if script_count == 0:
        print(f"[DIR] {folder_name} - No scripts to test")

# Assuming each subfolder in the current directory represents a separate test case
current_folder = os.path.dirname(os.path.abspath(__file__))
root_folder = os.path.dirname(current_folder)
subfolders = [f.path for f in os.scandir(root_folder) if f.is_dir()]
subfolders = sorted(subfolders)

@pytest.mark.parametrize("folder", subfolders)
def test_all_scripts(folder):
    start_time = time.time()
    try:
        run_tests_in_folder(folder)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"[PASS] {os.path.basename(folder)} completed in {execution_time:.2f}s")
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"[ERROR] {os.path.basename(folder)} failed after {execution_time:.2f}s")
        raise
