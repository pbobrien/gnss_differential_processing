# Differential GNSS Post-Processing Kinematics

This repository contains scripts and tools that perform post-processing kinematic (PPK) differential corrections on GNSS data collected using a base station and rover. The processing script was originally designed to work with Hi-Target antennae, but alterations can be made to work with any RINEX file containing markers within the rover RINEX files. 

## Dependencies 
This software makes use of the Python programming language and was built on Python 3.13.5. Additional package requirements can be found in the requirements.txt file. 

In order to run the differential correction and optional base station positioning, the [RTKLIB](https://github.com/tomojitakasu/RTKLIB)software must be installed. Ensure that the folder containing all of the RTKLIB information is placed in the same folder as the Python script. It can be placed in a different location, but the path will need to be entered manually before starting the processing. 

Because the processing is dependent on RTKLIB, only a computer running **Windows** should be used. This was tested on Windows 10 and Windows 11, so the use of other versions may very. 

In addition to RTKLIB, the file named basestationppp.conf should be in the same location as the .py file. The .py itself should be in the same directory as the RTKLIB folder. A Python IDE is recommended to run the program, but it can also be run from the command line. If a new Python setup is required, more information can be found on the [Official Python Website](https://docs.python.org/3.13/using/windows.html).

## Data Preparation 
To process differential GNSS data, it must be in RINEX format and contain both the .XXo (or .obs) and .XXp (or .nav) files from both the rover and base station. 

These data must be placed into a specific file structure (for now) in order to effectively access and process each dataset at a time. This usually takes the form of a set of base station RINEX files (.nav and .obs) files that are paired with all rover files collected within the base station files's time period. The following file structure should be as follows:
- Parent Directory
	- Base
	- Output
	- Rover

The base and rover files should go into their appropriately named directories, while the Output folder will contain any outputs from the program. The Output folder is cleared at the beginning of a new run involving the Parent Directory, so please be sure to save any data as needed before running the script again. 

This program is designed to work with a nested folder structure allowing for multiple sets of base station/rover pairs to be processed at once. To ensure this works smoothly, having the three directory arrangement (Base, Output, and Rover) for each desired processing period is recommended. 


### Base Station Data Preparation 
The geographic coordinates of the base station should ideally be known, but an option is available if the location of the base station has not yet been determined. When selected, the coordinates of the base station will be determined automatically, provided there is an internet connection. This is required to download additional data that is used to determine the position of the base station, and a printout of the location (latitude, longitude, height) along with the associated error (in m) is produced. This process currently makes use of final IGS products, so the base station can only be determined about two weeks after the data were collected. The IGS product type can be changed in the "check_precise_files()" function as the "product_mode" parameter. 

If there is no internet connection, the base station accuracy will be determined by calculating its static position. This will not be accurate compared to the above method, with an estimated uncertainty of 3+ metres. 

If the base station coordinates are known, ensure that the appropriate check box is selected and additional data fields will appear to enter the coordinates in decimal degrees. 


### Rover Data Preparation
While no specific rover data preparation is needed, potential tweaks may need to be included in the script in order to identify antennae-specific markers. The Hi-Target Antennae for which this script was originally designed utilize a marker value of " 3  4", but this will vary for different collection methods, including geotagged images from DJI drones. The marker value can be changed within the "event_write()" function of the script. 

All Markers (or events) contained within the rover files will be converted to " 5  0", which is then used by RTKLIB to appropriately reference the Markers. 


### Processing Notes
When processing data that originates from the same collection period, it is recommended to keep settings the same between each file. A utility within this program is to process multiple sets of files at once, so this is largely taken care of automatically. To ensure proper functioning, grouping datasets into sub-directories within a single parent directory is recommended before running the process. This will ensure that there are no inconsistencies when compiling data, especially in regards to the additional options that can be selected. 


## Using the Program 
The GNSS processing program was designed to automate as many steps as possible, requiring little intervention provided the Python environment was correctly set up and that the directory structure is correct. 

1. Ensure all files are in the correct folder, following the folder structure:
	- Parent directory
		- Base
		- Output
		- Rover
	Additional directories can exist between a parent directory and the three required folders, and this is recommended if multiple collection sets should be processed at the same time (e.g. samples were recorded on different days during the same field work). 
	A recommended way to do so is to divide the sub-directories by plot, day, or however else the data can be categorically organized. However this is organized, there should be one base station file associated with its corresponding Rover files, collected at the same time the base station file was running. 
	Once setup, note the preferred parent directory. Ensure that a folder containing RTKLIB is adjacent to the parent directory folder.

2. Run the program, whether through an IDE or using Command Prompt. If using Command Prompt, ensure that it is running from the folder containing the .py file and use the follow code as an example:
   "python gnss_differential_processing.py"
   Running this will create a GUI for which the remainder of the directions apply. 

3. Directory Selection
	- This section allows for the selection of the data-containing directory and the path to the executable file use from RTKLIB. 
	- Parent Directory - copy and paste or click on the three dots to navigate to the directory containing all of the sub-directories. 
	- Path to RTKLib's... - If the RTKLIB folder was placed in the same directory as the .py file, then it may have automatically been found. If not, either paste the path directly to "rnx2rtkp.exe" file, or use the three dots to browse to the file. 

4. Additional Options 
	There are currently three options that can be selected to change the processing and final products output by this program. Each checkbox has a label that shows the current status of the option. For example, "Flag potential duplicate?" is Disabled by default, but checking the box will enable this function. The status label will change when the item is selected and deselected.  
	a. Would you like to compile all events? 
		When set to "Enabled" (checked), this will copy all CSV files within the targeted directories into a directory labelled "CSV_Output". In addition, a master CSV file will be created in the "CSV_Output" directory containing the points from all CSV files. 
	b. Flag potential duplicates? 
		When set to "Enabled" (checked), this will determine if any two (or more) points were collected in the same location. This check occurs after the differential correction, and points are only flagged with they are within 0.000001 degrees of each other and were recorded more than 1 minute apart. These parameters can be changed in the dup_detect() function. 
	c. Base station location known
		The default state for this option is "No" (unchecked), meaning that a base station location has not been determined previously. If the program is run with the "No" option, the coordinates for the base station will be automatically determined for each separate Base folder. This will cause the program to have a longer run time, and coordinates of each base station will be printed out in the "Output" dialog box. 
		Checking the box will set the state to "Yes" and text boxes will appear to allow for the entry of the latitude, longitude, and height of the base station. Latitude and longitude should be in decimal degrees while the height is in metres above sea level. The entered values will be used for processing all files within the Parent Directory. 
		While this program can also be used to determine the base station position, other free programs are available online, including the [Natural Resources Canada Precise Point Positioning portal](https://webapp.csrs-scrs.nrcan-rncan.gc.ca/geod/tools-outils/ppp.php). Using this portal will generate a report and is recommended if the same base station location is used on multiple occasions. 
		
5. Output window
   This window displays text messages to provide updates about the processing steps of the program. Scrolling with a mouse will not currently work in the output window, so please use the scroll bar on the side. 
   *Most outputs, including errors, should show up here. It is recommended to keep an eye on the Python IDE or Command Prompt for additional error messages. *


## Outputs
There are several outputs produced by this program, the primary of which are .CSV files containing the differentially corrected rover data for each Marker. In addition, intermediate files are created with a .pos file ending that contain the differentially corrected information. The CSV files are created based on these .pos files, and have the following headers:

| Field                        | Description                                                                                                                                                                                                                                                                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Date, Time                   | Date and time (in UTC) when the Marker point was collected.                                                                                                                                                                                                                                                                           |
| Latitude, Longitude, Height: | Latitude and longitude are in decimal degrees, height is in metres.                                                                                                                                                                                                                                                                   |
| Q                            | The quality flag from the RTKLIB executable. The following values are possible: <br>	0. Fix (Invalid)<br>	1. Fixed (Centimetre level)<br>	2. Float (Decimetre/metre level)<br>	3. SBAS (SBAS corrected)<br>	4. DGPS (Differential GNSS - metre level)<br>	5. Single (standalone - metre level)<br>	6. PPP (Precise Point Positioning) |
| ns                           | Number of satellites.                                                                                                                                                                                                                                                                                                                 |
| sdn(m)                       | Standard deviation for latitude, in metres.                                                                                                                                                                                                                                                                                           |
| sde(m)                       | Standard deviation for longitude, in metres.                                                                                                                                                                                                                                                                                          |
| sdu(m)                       | Standard deviation for height, in metres.                                                                                                                                                                                                                                                                                             |
| PointID                      | Label assigned to the marker during collection.                                                                                                                                                                                                                                                                                       |
| DuplicateFlag                | (Optional) Binary field that indicates if points were recorded in the same location at different times.                                                                                                                                                                                                                               |

If the "Would you like to compile all events?" option is set to "Enabled", all CSV files within the target directories will be extracted and placed in to a directory labelled "CSV_Output". In addition, a master CSV file will be created in the aforementioned directory containing the points from all CSV files. 


## License 

See the license.txt file for more information for this program. For RTKLIB's license, please see below. 

### RTKLIB
https://github.com/tomojitakasu/RTKLIB

This software makes use of RTKLIB for the differential processing portion of this code. The licensing information for RTKLIB is included. 

Copyright (c) 2007-2013, T. Takasu, All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright notice, this
  list of conditions and the following disclaimer in the documentation and/or
  other materials provided with the distribution.

- The software package includes some companion executive binaries or shared
  libraries necessary to execute APs on Windows. These licenses succeed to the
  original ones of these software. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
