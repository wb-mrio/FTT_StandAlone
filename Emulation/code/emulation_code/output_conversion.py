# -*- coding: utf-8 -*-
"""
Created on Tue Dec 12 10:25:47 2023

Script for output processing, manipulation, and visualization

Simplified for batch processing with 200 scenarios at a time.

@author: ib400
"""

import os 
import pandas as pd
import numpy as np
import pickle

# Set the working directory
os.chdir(r'C:\Users\ib400\GitHub\FTT_StandAlone')
import SourceCode.support.titles_functions as titles_f

# Load title mappings
titles = titles_f.load_titles()
scen_levels = pd.read_csv('Emulation/data/scenarios/S3_scenario_levels.csv')

# Define variables to compare
vars_to_compare = ['MEWS', 'MEWK', 'MEWG', 'MEWE', 'MEWW', 'METC', 'MEWC', 'MECW']
scens_to_compare = list(scen_levels['ID'])

def load_output(scen_id):
    """Loads scenario output data."""
    output_path = f'Output/Results_{scen_id}_core.pickle'
    with open(output_path, 'rb') as file:
        return pickle.load(file)

def filter_output(output, vars_to_compare):
    """Filters the output data for selected variables."""
    return {key: value for key, value in output.items() if key in vars_to_compare}

def extract_to_df(output_data):
    """Extracts output data to a DataFrame."""
    data_records = []
    
    for scenario, variables in output_data.items():
        for variable, dimensions in variables.items():
            print(f'Converting {variable} for {scenario}')
            
            # Get indices for array data
            indices = np.indices(dimensions.shape).reshape(dimensions.ndim, -1).T
            for index in indices:
                value = dimensions[tuple(index)]
                year = index[3] + 2010
                tech = index[1]
                
                # Handle global vs country-level data
                if variable == 'MEWW':
                    country, country_short = 'Global', 'GBL'
                else:
                    country = titles['RTI'][index[0]]
                    country_short = titles['RTI_short'][index[0]]
                
                data_records.append({
                    'scenario': scenario,
                    'variable': variable,
                    'country': country,
                    'country_short': country_short,
                    'technology': titles['T2TI'][tech],
                    'year': year,
                    'value': value
                })
    
    return pd.DataFrame(data_records)

# Process each scenario individually, saving each as its own CSV file
for scen in scens_to_compare:
    # Load and filter output data for a single scenario
    output = filter_output(load_output(scen), vars_to_compare)
    
    # Convert to DataFrame
    scen_df = extract_to_df({scen: output})
    
    # Save each scenario to a separate CSV file
    scen_df.to_csv(f'Emulation/data/runs/{scen}_output.csv', index=False)
    print(f'Scenario {scen} saved with {len(scen_df)} rows')


print("Processing complete.")
