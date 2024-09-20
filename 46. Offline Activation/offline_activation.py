"""
To activate the SIMBA license required to use the aesim.simba library, there are two preferred options:

1. Activate SIMBA through the SIMBA.EXE graphical user interface (Windows only).
2. Use the License.Activate("YOUR_DEPLOYMENT_KEY") method as explained [here](https://www.simba.io/doc/python_api/overview/) (requires an internet connection).

If the target machine does not have an internet connection, a third option is available: Offline Activation.

- Using the SIMBA Python library, you can generate a SIMBA License Request File (.slr).
- This License Request file can then be uploaded to your profile page at https://simba.io/profile_account/, where you can download a new SIMBA license file (.slf).
- The SIMBA license file can be processed locally on the target machine without needing an internet connection.

The following example demonstrates how to use this method.
"""

import os
if os.environ.get("SIMBA_SCRIPT_TEST"): exit() # To exclude this example from our automated test base.


from aesim.simba import License

# Step 1: Specify the path where the .slr file will be saved and generate the license request file
license_request_file_path = "/path/to/the/slr/file.slr"
License.SaveLicenseRequestFile(license_request_file_path)  # Generate the license request file

# Step 2: Go to https://simba.io/profile_account/ (can be done on another computer)
# In the "Offline Activation" section, upload the .slr file and click on "Download" to obtain the SIMBA license file (.slf)

# Step 3: Specify the path to the downloaded .slf file and activate SIMBA
license_file_path = "/path/to/the/slf/license.slf"
License.LoadLicenseFile(license_file_path)  # Load the license file to activate SIMBA