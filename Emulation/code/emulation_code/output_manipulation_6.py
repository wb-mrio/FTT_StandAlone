# -*- coding: utf-8 -*-
"""
Created on Tue Dec 12 10:25:47 2023

Script for output processing, manipulation and visualisation

Developments and tasks:
    - Compare MCOCX and MCOC

@author: ib400
"""

import os 
import pandas as pd
import numpy as np
import matplotlib
import pickle
import SourceCode.support.titles_functions as titles_f

os.chdir(r'C:\Users\ib400\OneDrive - University of Exeter\Desktop\PhD\GitHub\FTT_StandAlone')
#%%
titles = titles_f.load_titles()

scen_levels = pd.read_csv('Emulation/data/scenarios/S3_scenario_levels.csv')

# combine scenario data and output
data = {}
for ID in scen_levels['ID']:
    # extract scen data and drop ID column
    data[ID] = {'scenario' : scen_levels.loc[scen_levels['ID'] == ID].drop('ID', axis=1)}
    
    # path to output of model runs
    output_path = f'Output/Results_{ID}_core.pickle'
    
    # Open the pickle file in binary mode and load its content
    with open(output_path, 'rb') as file:
        # Use pickle.load() to load the content into a dictionary
        output = pickle.load(file)
    
    # add output data
    data[ID].update({'output': output})

#%%
### Baseline

# path to output of model runs
emulation_scens = scen_levels['ID']
scens_to_compare = list(emulation_scens) # ['S0', 'S3']
countries_to_compare = ['US', 'CN', 'IN', 'DE', 'UK']
vars_to_compare =  ['MEWS', 'MEWK', \
                  'MEWG', 'MEWE', 'MEWW']
    
output_data = {}
for scen in scens_to_compare:
        
    output_path = f'Output/Results_{scen}_core.pickle'

    # Open the pickle file in binary mode and load its content
    with open(output_path, 'rb') as file:
        # Use pickle.load() to load the content into a dictionary
        output = pickle.load(file)
    
    filtered_output = {key: value for key, value in output.items() if key in vars_to_compare}
    output_data[scen] = filtered_output
    
#%%    
scenario_list = []
variable_list = []
country_list = []
country_short_list = []
technology_list = []
value_list = []
year_list = []

for scenario, variables in output_data.items():
    for variable, dimensions in variables.items():

        print(variable)
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
            

# Create DataFrame from the lists
df = pd.DataFrame({
    'scenario': scenario_list,
    'variable': variable_list,
    'country': country_list,
    'country_short' : country_short_list,
    'technology': technology_list,
    'value': value_list,
    'year': year_list
})

df.to_csv(f'Output\emulation_data_long.csv',
          index = False)


