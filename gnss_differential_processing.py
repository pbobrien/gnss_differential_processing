
# GNSS Differential Processing
# 
# Copyright (c) 2026, Patrick B. O'Brien, All rights reserved.
# https://github.com/pbobrien/gnss_differential_processing
# 
#
# RTKLIB 
# Copyright (c) 2007-2013, T. Takasu, All rights reserved.
# https://github.com/tomojitakasu/RTKLIB
#
#


#######################
## 0. Package Import ##
#######################

import os
import numpy as np
import pandas as pd
import shutil
import subprocess


import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import threading
import time

import re

import datetime
import urllib.request
import gzip



#########################
## 1. Script Functions ##
#########################

# Function - rewrites Marker sequence for events to standard code (" 5  0") 
# and saves original event details  
def event_write(in_path, out_path):

    # Initialize dictionary to record event (Marker) information
    event_dict = {"time": [], "name": [], "pos": [], "ant_del": []}

    check_list = []

    check = 0

    # Opening specified rover file on in_path
    with open(in_path) as fin, open(out_path, 'w') as fout:
        
        # Marker location (" 3  4" is for Hi-Target antennae)
        # Change this value if needed (rover collection method dependent)
        mark = " 3  4\n"

        # Iterates through file line-by-line to find instances of Marker location
        for line in fin:

            if mark in line:
                reline = line

                reline = reline.replace(mark, " 5  0\n")

                event_dict["time"].append(line)

                check = 5

                fout.write(reline)

            if check == 0:
                fout.write(line)

            check_list.append(check)

            if (check != 0):
                check = check-1
                if "MARKER" in line:
                    event_dict["name"].append(line)
                elif "APPROX" in line:
                    event_dict["pos"].append(line)
                elif "ANTENNA" in line:
                    event_dict["ant_del"].append(line)

    #print(np.unique(check_list, return_counts=True))
    # Saves the dictionary of Marker events to a pandas DataFrame
    event_df = pd.DataFrame(event_dict)

    return event_df


# Function - checks file types for "o" and "p", converts 
# to "obs" and "nav", respectively, where needed
def file_check(rinex_type, new_type, files):

    file_type = [fname for fname in files if rinex_type in fname]
    if (new_type in file_type) or (file_type == []):
        return 0, 0
    else:
        og_name = file_type[0]
        new_name = og_name[0:-3] + new_type
        return new_name, og_name


#Function - changes files' names and sets the correct path 
def file_type_convert(root, files):

    out_frame.after(0, printOut(files))
    main.update_idletasks()

    o_name_new, o_name_og = file_check("o", "obs", files)
    if (o_name_new != 0):
        obs_path = root + "\\" + o_name_new
        os.rename(root + "\\" + o_name_og, obs_path)
    elif (o_name_new == 0):
        obs_path = root + "\\" + [o_name for o_name in files if ".obs" in o_name][0]
    

    p_name_new, p_name_og = file_check("p", "nav", files)
    if (p_name_new != 0):
        nav_path = root + "\\" + p_name_new
        os.rename(root + "\\" + p_name_og, nav_path)
    else:
        nav_path = root + "\\" + [p_name for p_name in files if ".nav" in p_name][0]


    return obs_path, nav_path


# Function - runs rxn2rtkp.exe executable file from RTKLIB. 
# Settings can be changed in the code for now
def rtk_post_run(rxn_path, base_obs_path, base_info, rov_obs_path_mark, rov_nav_path, out_path):


    rtkpost_settings = [rxn_path, 
                        "-o", out_path, "-p", "2", "-m", "15", "-f", "3", "-c", "-l", str(base_info[0]), str(base_info[1]), str(base_info[2]), "-t", 
                        rov_obs_path_mark, base_obs_path, rov_nav_path]


    rtkpost_out = subprocess.run(rtkpost_settings, capture_output=True)


    return 0


# Base station coordinate determination 
# Run if base station coordinates not included in input

# Function - gets base station start date from RINEX file
def base_rinex_date(base_obs_path):
    """
    Reads the 'TIME OF FIRST OBS' line from RINEX header
    """
    #print(f"Base obs path: {base_obs_path}")

    try:
        with open(base_obs_path, 'r') as bf:
            for _ in range(100):
                line = bf.readline()
                if not line or "END OF HEADER" in line:
                    break
                if ("TIME OF FIRST OBS" in line):
                    parts = line.split()
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    if year < 100:
                        year += 1900 if year >= 80 else 2000
                    return datetime.date(year, month, day)
    except FileNotFoundError:
        print(f"Could not find {base_obs_path}")
        out_frame.after(0, printOut(f"Could not find {base_obs_path}"))
        main.update_idletasks() 
        return None
    out_frame.after(0, printOut(f"Error: Could not find 'TIME OF FIRST OBS' in the header."))
    main.update_idletasks() 
    return None


#Function - checks for precise products to avoid additional download
def check_precise_files(obs_date, product_mode='FIN', output_dir="."):
    """
    Checks if the uncompressed precise orbit and clock files 
    are already present in the target directory.
    """
    yyyy_ddd = obs_date.strftime("%Y%j") 
    
    # Construct the expected UNCOMPRESSED filenames
    orbit_file = os.path.join(output_dir, f"IGS0OPS{product_mode}_{yyyy_ddd}0000_01D_15M_ORB.SP3")
    clock_file_05m = os.path.join(output_dir, f"IGS0OPS{product_mode}_{yyyy_ddd}0000_01D_05M_CLK.CLK")
    clock_file_30s = os.path.join(output_dir, f"IGS0OPS{product_mode}_{yyyy_ddd}0000_01D_30S_CLK.CLK")
    
    existing_files = []
    
    # Check for the orbit file
    if os.path.exists(orbit_file):
        existing_files.append(orbit_file)
        
    # Check for the clock file (either 5-minute or 30-second fallback)
    if os.path.exists(clock_file_05m):
        existing_files.append(clock_file_05m)
    elif os.path.exists(clock_file_30s):
        existing_files.append(clock_file_30s)
        
    # We only return success if we found BOTH an orbit and a clock file
    if len(existing_files) == 2:
        return existing_files
        
    return None


#Function - downloads precise orbit and clock prodcuts from online
def precise_products_download(obs_date, root, product_type='FIN'):
    """
    Downloads precise orbit (.sp3) and clock (.clk) files from the BKG GNSS Data Center.
    An internet connection is required for this to function. 
    """
    
    gps_epoch = datetime.date(1980, 1, 6)
    delta = obs_date - gps_epoch
    gps_week = delta.days//7
    gps_day = delta.days%7 

    
    # Get year and day for new filename
    yyyy_ddd = obs_date.strftime("%Y%j")
    
    #Sets URL for BKG access
    base_url = f"https://igs.bkg.bund.de/root_ftp/IGS/products/{gps_week}/"
    download_files = [
        f"IGS0OPS{product_type}_{yyyy_ddd}0000_01D_15M_ORB.SP3.gz",
        f"IGS0OPS{product_type}_{yyyy_ddd}0000_01D_05M_CLK.CLK.gz"
    ]

    pp_files = []

    for filename in download_files:
        url = base_url + filename
        output_path = os.path.join(root, filename)
        print(f"Downloading {filename}...")
        try:
            urllib.request.urlretrieve(url, output_path)
            pp_files.append(output_path)

        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code} - Could not find {filename}.")
            
            # Fallback logic: If the 5-min clock file is missing, try the 30-second one
            if "CLK" in filename and "05M" in filename:
                print("Trying 30-second sampling (30S) fallback for clock file...")
                fallback_filename = filename.replace("05M", "30S")
                fallback_url = base_url + fallback_filename
                fallback_path = os.path.join(output_path, fallback_filename)
                try:
                    urllib.request.urlretrieve(fallback_url, fallback_path)
                    pp_files.append(fallback_path)
                except Exception as e2:
                    print(f"Failed fallback download. Error: {e2}")
        except Exception as e:
            print(f"Failed to download {filename}. Error: {e}")
            
    return pp_files


#Function - extracting precise files from .Z format
def extract_gz_files(filepath):
    """
    Extracts gzip files to uncompressed format
    """

    print(f"Extracting {filepath}...")
    extracted_path = filepath[:-3]

    try:
        with gzip.open(filepath, 'rb') as f_in:
            with open(extracted_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
                
        # Clean up the compressed archive after successful extraction
        os.remove(filepath) 
        return extracted_path
    except Exception as e:
        print(f"Extraction failed for {filepath}. Error: {e}")
        return None


#Function - processes base station file with rxn2rtkp.exe
def process_base_station(base_obs_path, base_nav_path, out_pos_file, conf_file, extra_files, rxn_path):
    """Runs RTKLIB's rnx2rtkp with all gathered files."""
    #print(extra_files)
    static_ppp_command = [
        rxn_path,
        "-o", out_pos_file,
        "-k", conf_file,
        base_obs_path,
        base_nav_path
    ] + extra_files # Append the .sp3 and .clk files to the end

    out_frame.after(0, printOut(f"Running RTKLIB Processing..."))
    main.update_idletasks() 
    try:
        subprocess.run(static_ppp_command, capture_output=True)
        out_frame.after(0, printOut(f"Processing successful. Solution saved to: {out_pos_file}"))
        main.update_idletasks() 
        return True
    except subprocess.CalledProcessError as e:
        out_frame.after(0, printOut(f"RTKLIB Processing failed.\nError output: {e.stderr}"))
        main.update_idletasks() 
        return False


# Function - computes average base station location
def get_base_loc(out_pos_file):
    """Parses the output .pos file and averages the coordinates."""

    if not os.path.exists(out_pos_file):
        return None
        
    lats, lons, heights = [], [], []
    std_lats, std_lons, std_h = [], [], []
    with open(out_pos_file, 'r') as file:
        for line in file:
            if line.startswith('%'):
                continue
            parts = line.split()
            if len(parts) >= 5:
                try:
                    lats.append(float(parts[2]))
                    lons.append(float(parts[3]))
                    heights.append(float(parts[4]))
                    std_lats.append(float(parts[7]))
                    std_lons.append(float(parts[8]))
                    std_h.append(float(parts[9]))
                except ValueError:
                    continue
                    
    if not lats:
        return None
    
    base_loc = [sum(lats)/len(lats), sum(lons)/len(lons), sum(heights)/len(heights),
                sum(std_lats)/len(std_lats), sum(std_lons)/len(std_lons), sum(std_h)/len(std_h)]
        
    return base_loc


# Function - removes pppstatic files from base folder 
def ppp_static_remove(root):

    base_dirs = os.listdir(root)

    for file in base_dirs:
        if "pppstatic" in file:
            os.remove(root + "\\" + file)



# Function - find base station coordinates
# Include printout
# Utilizes rxn2rtkp.exe in static mode 
def base_locate(rxn_path, base_obs_path, base_nav_path, conf_file, root):
    """
    Calls several functions to find the location of the base station.
    Outputs list of lat, long, and height
    """

    # Sets filename for static solution 
    out_pos_file = base_obs_path[0:-4] + "_pppstatic.pos"

    # Removes static files 
    ppp_static_remove(root)

    # Determines GPS time from base station .obs file
    obs_date = base_rinex_date(base_obs_path)

    precise_files = check_precise_files(obs_date, product_mode='FIN', output_dir=root)

    if precise_files:
        out_frame.after(0, printOut(f"Precision orbit and clock files exist in Base folder"))
        main.update_idletasks()
    else:
        # Download .sp3 and .clk files based on base station GPS time 
        ppz_files = precise_products_download(obs_date, root, product_type='FIN')


        precise_files = []

        # Extract files from .Z compressed format 
        for z_file in ppz_files:
            extracted = extract_gz_files(z_file)
            if extracted:
                precise_files.append(extracted)

    # Run RTKLIB's PPP static processing 
    if len(precise_files) == 2:
        process_base_station(base_obs_path, base_nav_path, out_pos_file, conf_file, precise_files, rxn_path)


    # Get final coordinates from average 
    base_location = get_base_loc(out_pos_file)
    if base_location:
        base_info = [np.round(base_location[0], 8), np.round(base_location[1], 8), np.round(base_location[2], 3)]

        out_frame.after(0, printOut(f"Using following coordinates for base station:"))
        out_frame.after(0, printOut(f"Latitude: {base_info[0]}; Longitude: {base_info[1]}; Height: {base_info[2]}"))
        out_frame.after(0, printOut(f"Errors: Latitude: {np.round(base_location[3], 4)} m; Longitude: {np.round(base_location[4], 4)} m; Height: {np.round(base_location[5], 4)} m"))
        main.update_idletasks()  

        ppp_static_remove(root)

        return base_info



# Section 2: Labelling Events
# This section puts the labels back to the PPP corrected files 
# Does this based on the date and time of collection 
# For now, only adds in the point name 


# Function - Assigns Marker information to points
def point_assign(pname, posdf, nidx, mark_df):

    event_list = mark_df.to_dict(orient='list')

    temp_name = event_list["name"][nidx].split()
    temp_name = [name for name in temp_name if name not in ['MARKER', 'NAME']]

    point_name = " ".join(temp_name)
    temp_dt = event_list["time"][nidx].split()[1:7]

    if len(temp_dt[1]) == 1:
        temp_dt[1] = "0" + temp_dt[1]
    if len(temp_dt[2]) == 1:
        temp_dt[2] = "0" + temp_dt[2]
    if len(temp_dt[4]) == 1:
        temp_dt[4] = "0" + temp_dt[4]
    if len(temp_dt[5]) == 9:
        temp_dt[5] = "0" + temp_dt[5]

    date = temp_dt[0] + "/" + temp_dt[1] + "/" + temp_dt[2]
    time = temp_dt[3] + ":" + temp_dt[4] + ":" + temp_dt[5][0:6]

    #print("Date and Time: ", date, time)
    #print("Position File times:", posdf[posdf["Time"] == time])

    name_idx = posdf.index[(posdf["Time"] == time) & (posdf["Date"] == date)]
    #print(f"Name idx {name_idx}")
    if (name_idx.size > 0):
        try:
            pname[name_idx[0]] = point_name
        except:
            print(f"Error with {point_name}")
            print(f"Name idx {name_idx}")
    else:
        pname = 0

    return pname


# Function - Creates a list of points
def point_list(posdf, mark_df):
    pname = [None]*len(posdf["Date"])
    for i in range(len(posdf["Date"])):
        pname = point_assign(pname, posdf, i, mark_df)

    return pname


# Function - Assigns values to each Marker point using DataFrame
def pos_process(pos_path, mark_df):
    """
    Pulls data from the "events" file produced in the Rover Directories. 
    """
    pos = [x for x in os.listdir(pos_path) if "events" in x]

    pos_arr = []

    header = []

    for e_file in pos:
        file = open(pos_path+ "\\" + e_file)
        for line in file:
            if (line[0] != '%'):
                fields = line.split()
                pos_arr.append(fields)
            elif ("latitude" in line and header == []):
                header = line.split()[2::]
                header = np.append(["Date", "Time"], header).tolist()

        file.close()

        posdf = pd.DataFrame(pos_arr, columns=header)

        #print(posdf)

        posdf.drop(columns=["sdne(m)", "sdeu(m)", "sdun(m)", "age(s)", "ratio"], inplace = True)

    list_name = point_list(posdf, mark_df)

    #print(list_name)
    out_frame.after(0, printOut(f"Number of points: {len(list_name)}"))
    main.update_idletasks()

    posdf["PointID"] = list_name

    return posdf


# Function - Writes out the Marker points to a CSV
def write_pos_csv(conv_df, pos_path):

    out_frame.after(0, printOut("Writing file to CSV"))
    main.update_idletasks()

    path_div = re.split(r"[\/\\]+", pos_path)
    fout = path_div[-2] + "_points.csv"
    #out_frame.after(0, printOut(f"Temp file name: {path_div}"))
    main.update_idletasks()
    out_path = pos_path + "\\" + fout

    out_frame.after(0, printOut(f"File location: {out_path}"))
    main.update_idletasks()

    conv_df.to_csv(out_path, index=False)
    out_frame.after(0, printOut("File written"))
    main.update_idletasks()

    return fout


# Function - Copies CSV files to CSV_Output directory
def out_collect(root, out_path, fout):

    shutil.copy2(root + "/" + fout, out_path + "/" + fout)


# Function - compiles all output csv files into one in CSV_Output directory
# Specific to Liana files, not used in the current release
def csv_lianas(csv_path):
    #csv_files = os.listdir(csv_path)

    out_frame.after(0,printOut(f"Extracting liana occupancy information"))
    main.update_idletasks()

    point_track = []

    fin_file = pd.read_csv(csv_path)


    point_df_keys = fin_file.keys().to_list()
    point_df_keys = point_df_keys.append("Lianas")

    point_df = pd.DataFrame({keys: [] for keys in point_df_keys})


    #for fin in csv_files:

        

        #fin_file = pd.read_csv(csv_path + "/" + fin)

        #if point_df.empty:
        #    point_df = pd.DataFrame({keys: [] for keys in fin_file.keys()})
        #    point_df["Lianas"] = []

    fin_file_len = len(fin_file["PointID"])

    out_frame.after(0, printOut(f"Number of points imported: {fin_file_len}"))
    

    true_points = fin_file[(fin_file["PointID"].str.contains("A|D") )]

    point_len = len(true_points["PointID"])

    out_frame.after(0, printOut(f"Number of valid points: {point_len}"))
    main.update_idletasks()

    point_track.append(len(true_points))

    a_points = fin_file[(fin_file["PointID"].str.contains("A") )]
    d_points = fin_file[(fin_file["PointID"].str.contains("D") )]

    q_points = fin_file[(fin_file["PointID"].str.contains("Q") )]

    #a_list = [None]*len(a_list["PointID"])
    a_list = []

    if len(a_points["PointID"]) > 0:
        for name in a_points["PointID"]:
            liana_cov = name.split("A", 1)[1]
            if len(liana_cov) > 1:
                liana_cov = liana_cov[1]
            a_list.append(liana_cov)

        a_points["Lianas"] = a_list

        point_df = pd.concat([point_df, a_points], ignore_index=True)


    d_list = []

    if len(d_points["PointID"]) > 0:
        for name in d_points["PointID"]:
            liana_cov = name.split("D", 1)[1]
            if len(liana_cov) > 1:
                liana_cov = liana_cov[1]
            d_list.append(liana_cov)

        d_points["Lianas"] = d_list

        point_df = pd.concat([point_df, d_points], ignore_index=True)
    #Bottom of previous for loop
            
    lian_len = len(point_df["Lianas"])
    out_frame.after(0, printOut(f"Total number of points processed: {np.sum(point_track)}"))
    out_frame.after(0, printOut(f"Total number of points written: {lian_len}"))
    point_df.to_csv(csv_path+ "/" + "liana_occupancy_events.csv", index=False)
    main.update_idletasks()


# Function - Compiles all csv's into one in CSV_Output directory
def csv_comp(csv_path):
    csv_files = os.listdir(csv_path)

    out_frame.after(0,printOut(f"Compiling CSV Files"))
    main.update_idletasks()

    point_df = pd.DataFrame({})

    for fin in csv_files:

        fin_file = pd.read_csv(csv_path + "/" + fin)

        if point_df.empty:
            point_df = pd.DataFrame({keys: [] for keys in fin_file.keys()})

        point_df = pd.concat([point_df, fin_file], ignore_index=True)

    point_len = len(point_df["PointID"])

    csv_out_path = csv_path + "/" + "All_Events.csv"

    out_frame.after(0, printOut(f"Total number of points written: {point_len}"))
    point_df.to_csv(csv_out_path, index=False)
    out_frame.after(0, printOut(f"Written to: {csv_out_path}"))
    main.update_idletasks()

    return csv_out_path


# Function - Creates flag in CSV for possible duplicate point
def dup_detect(conv_points, p_dist=0.000001, sec_diff=60):
    """
    Checks for duplicated points that were collected at different times.
    Current timing set to at least 60 seconds apart

    """

    # Keeps only one set of points since points are checked twice 
    processed = set()

    conv_points["date_time"] = pd.to_datetime(conv_points["Time"], format='%H:%M:%S.%f')

    # Creating a timedelta value
    time_diff = datetime.timedelta(seconds=sec_diff)

    for idx, row in conv_points.iterrows():


        # Looks at each row in conv_points and adds to matches
        nearby = conv_points[
            (np.abs(conv_points['latitude(deg)'].astype(float) - float(row['latitude(deg)'])) <= p_dist) &
            (np.abs(conv_points['longitude(deg)'].astype(float) - float(row['longitude(deg)'])) <= p_dist) &
            (conv_points.index != idx) &
            (np.abs(conv_points['date_time'] - row['date_time']) > time_diff)
        ]

        for idx_match, r_match in nearby.iterrows():
            key = tuple(sorted((idx, idx_match)))
            if not key in processed:
                processed.add(key)
        
    # Creates list of points to flag
    unq_idx = list(set([i for sub_tup in processed for i in sub_tup]))
    conv_points["DuplicateFlag"] = conv_points.index.isin(unq_idx)

    # Converts to integer
    conv_points["DuplicateFlag"] = conv_points["DuplicateFlag"].astype(int)

    # Drops temp "date_time" column
    conv_points.drop(columns=["date_time"], inplace=True)


    return conv_points


# Function - performs differential correction
def longrun_task():
    
    # Sets path variables from entry
    main_path = in_entry.get()
    rxn_path = rxn_entry.get()

    # Sets duplicate flag state
    dup_check = flag_var.get()

    # Determines base station coordinates a
    # If coordinates are included, proceeds with differential
    # If no coordinates included, determines base station position 
    # for each unique base station directory included in the path
    base_inc = base_var.get()

    if base_inc == 1:
        base_lat = base_input_lat.get()
        base_lon = base_input_lon.get()
        base_hei = base_input_hei.get()

        base_info = [base_lat, base_lon, base_hei]

        try:
            [float(i) for i in base_info]
        except ValueError:
            out_frame.after(0, printOut(f"Base coordinates are not properly formatted"))
            main.update_idletasks()
        except:
            out_frame.after(0, printOut(f"Base coordinates are not properly formatted"))
            main.update_idletasks()           

    out_frame.after(0, printOut(f"Working in {main_path}"))
    main.update_idletasks()

    comp_files = False

    if com_var.get() == 1:
        comp_files = True

    #liana_files = False
    #if lia_var.get() == 1:
    #    liana_files = True

    
    if comp_files:
        csv_path = "/".join(re.split(r"[/\\]+", main_path)[0:-1]) + "/CSV_Output"
        print(csv_path)
        if not os.path.exists(csv_path):
            os.mkdir(csv_path)
        else:
            csv_outs = os.listdir(csv_path)
            if len(csv_outs) > 0:
                for csv in csv_outs:
                    os.remove(csv_path+"/"+csv)


    for (root,dirs,files) in os.walk(main_path,topdown=True):


        if "Output" in root:
            pos_out_path = root
            
            #Clearing output folder in case there is something in there

            if len(files) > 0:
                for f in files:
                    os.remove(root+"\\"+f)

        

        if len(files) > 0:
            out_frame.after(0,printOut(f"Directory path: {root}"))
            main.update_idletasks()

            if ("Base" in root) and (len(files) > 1):

                base_obs_path, base_nav_path = file_type_convert(root, files)

                if base_inc == 0:
                    out_frame.after(0, printOut(f"Determining position of base station..."))
                    main.update_idletasks()

                    # Calls base_locate() to determine location
                    # Calls rxn2rtkp.exe for static position determination 
                    base_info = base_locate(rxn_path, base_obs_path, base_nav_path, conf_file, root)

                

            if ("Rover" in root) and (len(files) > 1):
            
                rov_files = [nomark for nomark in files if "nomark" not in nomark]
                rov_file_len = len(rov_files)


                rov_nav_list = []

                mark_df = pd.DataFrame({"time": [], "name": [], "pos": [], "ant_del": []})
                
                for fname in rov_files:
                    if ("p" in fname) or ("nav" in fname):
                        rov_nav_list.append(root+"\\"+fname)

                i = 0
                while i < rov_file_len:
                    rov_obs = rov_files[i]
                    rov_nav = rov_files[i+1]

                    rov_obs_path, rov_nav_path = file_type_convert(root, [rov_obs,rov_nav])

                    rov_obs_path_mark = rov_obs_path[0:-4] + "_nomark" + rov_obs_path[-4::]

                    mark_df_out = event_write(rov_obs_path, rov_obs_path_mark)

                    mark_df = pd.concat([mark_df, mark_df_out])

                    pos_out = pos_out_path + "\\" + rov_obs[0:-3] + "pos"

                    out_frame.after(0, printOut("Differential processing current files"))
                    
                    rtk_post_run(rxn_path, base_obs_path, base_info, rov_obs_path_mark, base_nav_path, pos_out)


                    #conv_points = pos_process(pos_out_path)

                    #write_pos_csv(conv_points, pos_out_path)

                    i += 2                
                    
                conv_points = pos_process(pos_out_path, mark_df)

                # Check if duplicate flag is desired
                if dup_check == 1:
                    dup_detect(conv_points)

                fout = write_pos_csv(conv_points, pos_out_path)

                if comp_files == True:
                    out_frame.after(0, printOut(f"Copying CSV to {csv_path}"))
                    main.update_idletasks()
                    out_collect(pos_out_path, csv_path, fout)
        

        #out_frame.after(0, clearOut())
        #main.update_idletasks()

    if comp_files == True:
        csv_out_file = csv_comp(csv_path)

    #if liana_files==True:
    #    csv_lianas(csv_out_file)
    
    out_frame.after(0, printOut("Finished"))
    #main.destroy()


# Function - called with press of start button 
# Calls longrun_task function
def start_task():
    #clearOut()
    thread = threading.Thread(target=longrun_task)
    thread.start()


# Function - prints messages to Output field in GUI
def printOut(printtext):
    out_message = tk.Label(out_frame, text=printtext, bg="white")
    out_message.pack(anchor=tk.W)


# Function - browser for the parent directory 
def browseDirs():
    dirname = filedialog.askdirectory(initialdir=initdir, title="Select the parent folder")
    in_entry.delete(0, tk.END)
    in_entry.insert(0, dirname)


# Function - browser for the RXN2RTKP.exe file 
def browseRXN():
    rxn_path = filedialog.askopenfilename(initialdir=initdir, title="Select the rxn2rtkp.exe file")
    rxn_entry.delete(0, tk.END)
    rxn_entry.insert(0, rxn_path)


# Function - responds to the checkbox for compiling CSVs
def button_com():
    event = com_var.get()
    if com_var.get() == 1:
        com_check.configure(text="Enabled")
        #lia_appear(event)
    else:
        com_check.configure(text="Disabled")
        #lia_appear(event)


# Function - responds to duplicate flag
def button_flag():
    event = flag_var.get()
    if event == 1:
        flag_check.configure(text="Enabled")
    else:
        flag_check.configure(text="Disabled")


# Function - reponds to base station known (base_var)
def button_base():
    event = base_var.get()
    if event == 1:
        base_check.configure(text="Yes")
        base_coord_appear(event)
    else:
        base_check.configure(text="No")
        base_coord_appear(event)


# Function -  reveals base station coordinate entry 
def base_coord_appear(event):
    if event == 1:
        base_input_lat.grid(row=12, column=1, padx=5, pady=5, sticky=tk.NSEW)
        base_input_lon.grid(row=13, column=1, padx=5, pady=5, sticky=tk.NSEW)
        base_input_hei.grid(row=14, column=1, padx=5, pady=5, sticky=tk.NSEW)
    else:
        base_check.configure(text="No")
        base_input_lat.grid_forget()
        base_input_lon.grid_forget()
        base_input_hei.grid_forget()
        base_var.set(0)


''' Removed functions related to liana information extraction
# Function - provides liana information for events
# Disabled for general release

def lia_appear(event):
    if event == 1:
        lia_label.grid(row=6, column=1, sticky=tk.N)
        lia_check.grid(row=7, column=1, sticky=tk.N)
    else:
        lia_check.configure(text="No")
        lia_label.grid_forget()
        lia_check.grid_forget()
        lia_var.set(0)

#Function - checks state of lia button
# Disabled for general release
def button_lia():
    if com_var.get() == 1:
        lia_appear(com_var.get())
        if lia_var.get() == 1:
            lia_check.configure(text="Yes")
        else:
            lia_check.configure(text="No")
    else:
        lia_appear(com_var.get())
''' 


# Function - clears output (not working yet)
def clearOut():

    time.sleep(1)
    for widget in out_frame.winfo_children():
        widget.destroy()

    #out_title = tk.Label(out_frame, text="Output", bg="black", fg="white", font=h3)
    #out_title.pack(anchor=tk.W)



###################################
## 3. Setting Initial Parameters ##
###################################

# Setting initial variables

# Retrieves directory containing this script
initdir = os.path.abspath(__file__)
temp_dir = initdir.split("\\")
initdir = "\\".join(temp_dir[0:-1]) + "\\"

# Setting font variables for tkinter GUI
h1 = ("Arial", 24, "bold")
h2 = ("Arial", 20, "bold")
h3 = ("Arial", 16)
p = ("Arial", 14)


# Setting path to rxn2rtkp.exe file
# Searches the directories in which this python file is contained
rxn_path = "None"
conf_file_path = "None"
for (root, dirs, files) in os.walk(initdir, topdown=True):
    if "rnx2rtkp.exe" in files:
        rnx2_file = [rnx2 for rnx2 in files if rnx2 == "rnx2rtkp.exe"]
        rxn_path = os.path.join(root, rnx2_file[0])
    elif "basestationppp.conf" in files:
        conf_path = [conf for conf in files if conf == "basestationppp.conf"]
        conf_file = os.path.join(root, conf_path[0])



#######################
## 4. GUI Components ##
#######################


# Establishes GUI for main window 
main = tk.Tk()

# Set main window title 
main.title("GNSS Processing")

# Sets title in main window 
main_title = tk.Label(main, text="GNSS Kinematic Conversion Program", font=h1)
main_title.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky=tk.NSEW)

# Describes function of program
main_desc = tk.Label(main, text="This program is designed to convert RINEX files collected a rover antenna (originally designed for Hi-Target systems)" \
" to produce event files that are associated with labelled events. Please make sure that you have read the instructions thoroughly and that the folders"
" and files are organized in the appropriate structure.", font=p, wraplength=600, justify="left")
main_desc.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.NW)


# Horizontal separator 
separator = ttk.Separator(main, orient='horizontal')
separator.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)


# Establishes parent directory with user input 
# Used to set "main_path" variable 
main.columnconfigure(1, weight=1)
in_title = tk.Label(main, text="Selecting the parent directory", font=h3).grid(row=3, column=0, columnspan=3, pady=5, padx=5, sticky=tk.W)
in_label = tk.Label(main, text="Parent Directory", font=p).grid(row=4, column=0, pady=5, padx=5, sticky=tk.E)
in_entry = tk.Entry(main)
in_entry.insert(0, "Please enter parent directory here...")
in_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.NSEW)
in_button = tk.Button(main, text="...", command=lambda : browseDirs())
in_button.grid(row=4, column=2, padx=5, pady=5, sticky=tk.E)

#Establishing rtklib_path input
#rxn_title = tk.Label(main, text="Path to RTKLib's rxn2rtkp.exe executable file", font=h3).grid(row=5, column=0, columnspan=3, pady=5, padx=5, sticky=tk.W)
rxn_label = tk.Label(main, text="rxn2rtkp Executable", font=p).grid(row=5, column=0, pady=5, padx=5, sticky=tk.E)
rxn_entry = tk.Entry(main)

# Determines if RXN2RTKP.exe was found by the search program
# Selects printout based on if it is found
if rxn_path == "None":
    tk.Label(main, text="Path to RTKLib's rxn2rtkp.exe executable file (must be specified)", font=h3).grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
    rxn_entry.insert(0, "Please copy or find directory containing the rnx2rtkp.exe file...")
else:
    tk.Label(main, text="Path to RTKLib's rxn2rtkp.exe executable file", font=h3).grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
    rxn_entry.insert(0, rxn_path)
rxn_entry.grid(row=6, column=1, padx=5, pady=5, sticky=tk.NSEW)
rxn_button = tk.Button(main, text="...", command=lambda : browseRXN())
rxn_button.grid(row=6, column=2, padx=5, pady=5, sticky=tk.E)


# Horizontal separator 
separator = ttk.Separator(main, orient='horizontal')
separator.grid(row=7, column=0, columnspan=2, sticky='ew', pady=5)


#Establishing variable for progress bar
#progress_var = tk.IntVar()

#Establishing and placing progress bar
#progress_bar = ttk.Progressbar(main, variable=progress_var, maximum=10)
#progress_bar.grid(row=7, column=1, columnspan=3, pady=20)

#Creating a button that will allow the option to compile all CSVs into one
#Setting toggled variable
com_var = tk.IntVar()
#lia_var = tk.IntVar()
flag_var = tk.IntVar()
base_var = tk.IntVar()

com_label = tk.Label(main, text="Would you like to compile all events?")
com_label.grid(row=8, column=0, pady=5, padx=5, sticky=tk.N)

com_check = tk.Checkbutton(main, text="Disabled", variable=com_var, onvalue=1, offvalue=0, command=button_com)
com_check.grid(row=9, column=0, sticky=tk.N)

#Additional button for liana column that disappears when com_check is disabled
#lia_label = tk.Label(main, text="Would you like to add a column about liana occupancy?")
#lia_label.grid(row=6, column=1, pady=5, padx=5, sticky=tk.N)

#lia_check = tk.Checkbutton(main, text="No", variable=lia_var, onvalue=1, offvalue=0, command=button_lia)
#lia_check.grid(row=7, column=1, sticky=tk.N)


# Button to set flag for possible duplicate point
dup_flag_label = tk.Label(main, text="Flag potential duplicates?")
dup_flag_label.grid(row=8, column=1, pady=5, padx=5, sticky=tk.N)

flag_check = tk.Checkbutton(main, text="Disabled", variable=flag_var, onvalue=1, offvalue=0, command=button_flag)
flag_check.grid(row=9, column=1, sticky=tk.N)


# Button to indicate if base station information is known 
base_state_label = tk.Label(main, text="Base Station location known?")
base_state_label.grid(row=10, column=0, pady=5, padx=5, sticky=tk.N)

base_check = tk.Checkbutton(main, text="No", variable=base_var, onvalue=1, offvalue=0, command=button_base)
base_check.grid(row=11, column=0, sticky=tk.N)

# Input for base station coordinates
base_input_lat = tk.Entry(main)
base_input_lat.insert(0, "Latitude (Decimal Degrees)")
#base_input_lat.grid(row=12, column=1, padx=5, pady=5, sticky=tk.NSEW)

base_input_lon = tk.Entry(main)
base_input_lon.insert(0, "Longitude (Decimal Degrees)")
#base_input_lon.grid(row=12, column=1, padx=5, pady=5, sticky=tk.NSEW)

base_input_hei = tk.Entry(main)
base_input_hei.insert(0, "Height Above Sea Level (m)")


#Establishing and placing start button
start_button = tk.Button(main, text="Start", command=start_task)
start_button.grid(row=15, column=0, pady=10, padx=10, sticky=tk.EW)

# Horizontal separator 
separator = ttk.Separator(main, orient='horizontal')
separator.grid(row=16, column=0, columnspan=2, sticky='ew', pady=5)


# Output window title
out_title = tk.Label(main, text="Output", font=h3)
out_title.grid(row=17, column=0, pady=5, padx=5, sticky=tk.W)

scroll = ScrolledText(main, state='disable')
scroll.grid(row=18, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NSEW)

# Create output frame 
out_frame = tk.Frame(scroll, bg="white")
scroll.window_create("1.0", window=out_frame)
#out_frame.grid(row=9, column=0, columnspan=3, padx=10, pady=10, sticky=tk.NW + tk.NE)

main.mainloop()



