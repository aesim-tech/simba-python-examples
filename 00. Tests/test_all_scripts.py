# test_script_execution.py
# Run all the scripts 
import os
import subprocess
import pytest
import nbformat
import sys
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
    subprocess.check_output([python_command, path], stderr=subprocess.STDOUT, universal_newlines=True, env=env)

def run_jupyter_notebook(path):
    original_cwd = os.getcwd()  # Save the original current working directory
    notebook_dir = os.path.dirname(path)  # Get the notebook's directory

    try:
        os.chdir(notebook_dir)  # Change to the notebook's directory

        with open(path) as f:
            nb = nbformat.read(f, as_version=4)
            ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

            try:
                ep.preprocess(nb, {'metadata': {'path': notebook_dir}})
                print(f"Successfully executed {path}")
            except CellExecutionError as e:
                print(f"Error executing {path}: {e}")
                raise

    finally:
        os.chdir(original_cwd)  # Revert back to the original directory

def run_tests_in_folder(folder_path):

    if 'JMAG' in folder_path and not sys.platform.startswith('win'):
        return # JMAG works only on windows
    
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if file.endswith(".py"):
            run_python_script(full_path)
        elif file.endswith(".ipynb"):
            run_jupyter_notebook(full_path)

# Assuming each subfolder in the current directory represents a separate test case
current_folder = os.path.dirname(os.path.abspath(__file__))
root_folder = os.path.dirname(current_folder)
subfolders = [f.path for f in os.scandir(root_folder) if f.is_dir()]
subfolders = sorted(subfolders)

@pytest.mark.parametrize("folder", subfolders)
def test_all_scripts(folder):
    run_tests_in_folder(folder)
