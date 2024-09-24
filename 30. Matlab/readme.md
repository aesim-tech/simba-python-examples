---
tags:
  - Python
  - Matlab
---

# Run Simba from Matlab with Simba python library

[Download **Python script**](flyback_script.py)


This case shows the capability to run a Python script from Matlab with the SIMBA Python library: a python script named *"Flyback.py"* is run from *Matlab* with the command: `pyrunfile(file_name.py)`.

!!! information "More information [here about the pyrunfile](https://fr.mathworks.com/help/matlab/ref/pyrunfile.html) function."

## Set-up procedure

Here is the procedure to follow before running a python script from Matlab:

1. Check the Python version that you are using is compatible with the Matlab version installed in your computer on this [Mathworks webpage](https://fr.mathworks.com/support/requirements/python-compatibility.html).
2. Set the PYTHONPATH environment variable:
     * for easier manipulation, a *system* environment variable named PYHOME can first be set - according to your python installation location - in the OS settings:
     ```
     PYHOME C:/Users/JohnDoe/AppData/Local/Programs/Python/Python310
     ```
     * then, the PYTHONPATH environment variable can be defined:
     ```
     PYTHONPATH  %PY_HOME%/Lib;%PY_HOME%/DLLs;%PY_HOME%/Lib/lib-tk;%PY_HOME%/Scripts/;%PY_HOME%/Lib/site-packages
     ```

??? tip "How to resolve a possible error *Tclerror* when calling python from Matlab?"

    TCL uses hard coded location of *tcl_library_path* to find its initialization files which does not work when Python is loaded by Matlab.
    More information could be found [there](https://fr.mathworks.com/matlabcentral/answers/1842093-how-to-resolve-error-calling-python-from-matlab).

    In such cases, it is possible to run in a Matlab console the following commands to set the <span style='color:red'>tcl8.6</span> and <span style='color:red'>tk8.6</span> library paths:

    ```
    setenv('TCL_LIBRARY', 'C:/Users/JohnDoe/AppData/Local/Programs/Python/Python310/tcl/tcl8.6');
    setenv('TK_LIBRARY', 'C:/Users/JohnDoe/AppData/Local/Programs/Python/Python310/tcl/tk8.6');
    py.tkinter.Tk;
    ```
    These lines have be changed according to your Python installation.

    As these commands have to be run every time you run Matlab, it is possible to write them in an initialization script, such as the *start.m* file. An example of this startup file can be [downloaded here](start.m).

    Matlab can be restarted to run its startup file or this startup file can be run manually:

    ```
    run("<set_location_path>/start.m")
    ```

## SIMBA circuit

Below the Flyback power converter used for this case. This example comes from the existing SIMBA collection of design examples.

![flyback](fig/flyback.png)


## Python Script

The Python script run from Matlab will do the following tasks:

* Load the flyback power converter from existing SIMBA collection of examples,
* Run a transient analysis and get the ouput voltage accross $R_2$ resistance,
* Create an array named **result** which contains both time and voltage vectors,
* Plot the output voltage $V_{R_2}$ with matplotlib module.


## Matlab GUI


To check the previous set-up, the following line can be run in a matlab command window:

```
py.math.sqrt(4)
```
You should get the answer : *ans = 2*

Now let's run the command below to simulate a flyback converter:

```
pyrunfile("<filepath>/Flyback.py")
```

Once executed you should obtain this behavior:

![result](fig/result.png)


## Conclusion

We can also type this below command in order to display in Matlab the array defined in the script which host both time and output voltage values:

```
result = pyrunfile("<filepath>/Flyback.py","result")
```

Once executed you should obtain this behavior:

![result1](fig/result1.png)

Now this array is also created in Matlab and can be retrieved for later manipulation.