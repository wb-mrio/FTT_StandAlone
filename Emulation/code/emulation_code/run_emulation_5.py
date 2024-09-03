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
import configparser
import subprocess

os.chdir('C:\\Users\\ib400\\GitHub\\FTT_StandAlone')

#%%

def scenario_list(file_path):
    
    # Path to input folder
    file_path = file_path
    
    # Get a list of all entries in the directory
    entries = os.listdir(file_path)
    
    # Filter entries to include only new scenarios 
    folder_names = [entry for entry in entries if os.path.isdir(os.path.join(file_path, entry)) \
                    and not entry.startswith('_MasterFiles') and not entry.startswith('S2') 
                    and not entry.startswith('S1')]


    sorting_key = lambda x: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', x)]

    # Sort folder names using the custom sorting key
    sorted_folder_names = sorted(folder_names, key=sorting_key)
    
    
    return sorted_folder_names

#%%

import configparser
import subprocess

def process_scenarios(all_scenarios, batch_size=2, config_path='settings.ini', script_path='run_file.py'):
    error_scenarios = []

    config = configparser.ConfigParser()
    
    # Process scenarios in batches
    for i in range(0, len(all_scenarios), batch_size):
        batch = ["S0"] + all_scenarios[i:i + batch_size]
        print(f"Processing scenarios for this batch: {batch}")
        
        try:
            # Load and update the settings file with the current batch of scenarios
            config.read(config_path)

            # Ensure the section exists
            if 'settings' not in config:
                print('error')
                config.add_section('settings')
            
            config['settings']['scenarios'] = ', '.join(batch)

            # Write the updated settings back to the file
            with open(config_path, 'w') as configfile:
                config.write(configfile)
                print(f"Updated {config_path} with scenarios: {batch}")
                
            # Optionally, run the simulation script
            subprocess.run(['python', script_path], check=True)

        except Exception as e:
            # Store the scenarios that caused the error
            error_scenarios.extend(batch)
            print(f"Error processing batch {batch}: {e}")
    
    # After processing, report any errors
    if error_scenarios:
        print("The following scenarios caused errors and were skipped:")
        for scenario in error_scenarios:
            print(scenario)
    else:
        print("All scenarios processed successfully.")

def main():
    # Define all the scenarios you want to run except baseline
    all_scenarios = [f"S3_{i}" for i in range(0, 7)]  

    # Process the scenarios with a batch size of 50
    process_scenarios(all_scenarios)








#%%

main()

# %%
if __name__ == "__main__":
    main()