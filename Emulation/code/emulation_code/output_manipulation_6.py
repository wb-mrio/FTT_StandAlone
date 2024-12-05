# -*- coding: utf-8 -*-
"""
Created on Tue Dec 12 10:25:47 2023

Script for output processing, manipulation and visualisation

Developments and tasks:
    - Compare MCOCX and MCOC

@author: ib400
"""
#%%

import os 
import pandas as pd
import numpy as np
import matplotlib
import pickle

os.chdir(r'C:\Users\ib400\GitHub\FTT_StandAlone')
import SourceCode.support.titles_functions as titles_f

#%%
titles = titles_f.load_titles()

scen_levels = pd.read_csv('Emulation/data/scenarios/S3_scenario_levels.csv')

# combine scenario data and output
data = {}

# iterate over scenarios
for ID in scen_levels['ID']:
    # extract scen data and drop ID column
    data[ID] = {'scenario' : scen_levels.loc[scen_levels['ID'] == ID].drop('ID', axis=1)}
    
    # path to output of model runs
    output_path = f'Output/Results_{ID}_core.pickle'
    
    # Open the pickle file in binary mode and load its content
    with open(output_path, 'rb') as file:
        # load the content into a dictionary
        output = pickle.load(file)
    
    # add output data
    data[ID].update({'output': output})

#%%
### Baseline

# path to output of model runs
emulation_scens = scen_levels['ID']
scens_to_compare = list(emulation_scens) # ['S0', 'S3']
vars_to_compare =  ['MEWS', 'MEWK', \
                  'MEWG', 'MEWE', 'MEWW', 'METC', 'MEWC', 'MECW']
    
output_data = {}
for scen in scens_to_compare:
        
    output_path = f'Output/Results_{scen}_core.pickle'

    # Open the pickle file in binary mode and load its content
    with open(output_path, 'rb') as file:
        # Use pickle.load() to load the content into a dictionary
        output = pickle.load(file)
    
    filtered_output = {key: value for key, value in output.items() if key in vars_to_compare}
    output_data[scen] = filtered_output
    
#%% Convert output data to DataFrame

# Create lists to store the data
scenario_list = []
variable_list = []
country_list = []
country_short_list = []
technology_list = []
value_list = []
year_list = []

for scenario, variables in output_data.items():
    for variable, dimensions in variables.items():

        print(f'Converting {variable} for {scenario}')
        if variable == 'MEWW':
            indices = np.indices(dimensions.shape).reshape(dimensions.ndim, -1).T

            # Iterate over the indices and extract values
            for index in indices:
                # Index corresponds to dimension in the np array
                value = dimensions[tuple(index)]
                
                # Append data to lists as though accessing dimensions of vars
                scenario_list.append(scenario)
                variable_list.append(variable)
                country_list.append('Global') 
                country_short_list.append('GBL')
                tech = index[1] 
                technology_list.append(titles['T2TI'][tech])  
                year = index[3] + 2010
                year_list.append(year)
                
                # Append value to the value list
                value_list.append(value) 
                
        else:
            # Flatten the array and get the indices
            indices = np.indices(dimensions.shape).reshape(dimensions.ndim, -1).T
    
            # Iterate over the indices and extract values
            for index in indices:
                
                # Index corresponds to dimension in the np array
                value = dimensions[tuple(index)]
                # Append data to lists as though accessing dimensions of vars
                scenario_list.append(scenario)
                variable_list.append(variable)
                country = index[0]
                country_list.append(titles['RTI'][country])  
                country_short_list.append(titles['RTI_short'][country])
                tech = index[1] 
                technology_list.append(titles['T2TI'][tech])  
                year = index[3] + 2010
                year_list.append(year)
                
                # Append value to the value list
                value_list.append(value) 
            
#%%
# Create DataFrame from the lists
df = pd.DataFrame({
    'scenario': scenario_list,
    'variable': variable_list,
    'country': country_list,
    'country_short' : country_short_list,
    'technology': technology_list,
    'year': year_list,
    'value': value_list
})

#%%
# Calculate number of batches
num_batches = len(df['scenario'].unique())
batch_size = len(df) // num_batches

# Iterate over batches and save each one
for i in range(200):
    start_index = i * batch_size
    end_index = (i + 1) * batch_size
    batch_df = df.iloc[start_index:end_index]  # Get a chunk of the DataFrame
    batch_df.to_csv(f'Emulation/data/runs/batch_{i}.csv', index=False)  # Save the batch to a CSV file
    print(f'Batch {i}/{num_batches} saved')

remaining_rows = len(df) % num_batches
# if remaining_rows > 0:
#     last_batch = df.iloc[-remaining_rows:]
#     last_batch.to_csv(f'Emulation/data_r/batch_{i}.csv', index=False)
#     print(f'Last batch of {remaining_rows} saved')
# %%
