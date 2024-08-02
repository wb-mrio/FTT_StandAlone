# -*- coding: utf-8 -*-
"""
Created on Tue Nov 14 10:20:09 2023

Function for taking all scenarios in inputs folder
Develop to input directly in settings.ini 
@author: ib400
"""

import os
import pandas as pd
import numpy as np
import re

os.chdir('C:\\Users\\ib400\\OneDrive - University of Exeter\\Desktop\\PhD\\GitHub\\FTT_StandAlone')

#%%

def scenario_list(file_path):
    
    # Path to input folder
    file_path = file_path
    
    # Get a list of all entries in the directory
    entries = os.listdir(file_path)
    
    # Filter entries to include only new scenarios 
    folder_names = [entry for entry in entries if os.path.isdir(os.path.join(file_path, entry)) \
                    and not entry.startswith('_MasterFiles') and not entry.startswith('S2') and not entry.startswith('S1')]


    sorting_key = lambda x: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', x)]

    # Sort folder names using the custom sorting key
    sorted_folder_names = sorted(folder_names, key=sorting_key)
    
    # Create a string of all folder names without quotes between each value
    result_string = ', '.join(sorted_folder_names)
    
    return result_string

#%%
import configparser
import subprocess

def update_settings_file(scenarios, config_path='settings.ini'):
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Update the scenarios in the settings file
    config['settings']['scenarios'] = ', '.join(scenarios)
    
    # Write the updated settings back to the file
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def run_simulation_script(script_path='run_simulation.py'):
    # Run the script using subprocess
    subprocess.run(['python', script_path], check=True)

def main():
    # Define all the scenarios you want to run
    all_scenarios = [f"S{i}" for i in range(100)]
    
    # Batch size
    batch_size = 50
    
    # Split the scenarios into batches and run them
    for i in range(0, len(all_scenarios), batch_size):
        batch = all_scenarios[i:i + batch_size]
        update_settings_file(batch)
        run_simulation_script()

if __name__ == "__main__":
    main()




#%%
scens = scenario_list(file_path = 'C:\\Users\\ib400\\OneDrive - University of Exeter\\Desktop\\PhD\\GitHub\\FTT_StandAlone\\Inputs')

