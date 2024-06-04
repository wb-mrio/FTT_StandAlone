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
import matplotlib.pyplot as plt
import pickle
import sys

#%% Importing local functions
# Get the root directory (assuming your script is one level deep in SourceCode)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

# Now you can import the module
import SourceCode.support.titles_functions as titles_f

#%% Loading and processing data
titles = titles_f.load_titles()

scenario = 'S0'

# path to output of model runs
output_path = f'../Output/Results_{scenario}.pickle'

# Open the pickle file in binary mode and load its content
with open(output_path, 'rb') as file:
    # Use pickle.load() to load the content into a dictionary
    output = pickle.load(file)

vars_to_compare =  ['MEWS', 'MSRC']
output = {key: value for key, value in output.items() if key in vars_to_compare}

#%% Producing csvs for data

for var in output.keys():
    for r in range(len(titles['RTI_short'])):
        region = titles['RTI_short'][r]
        country_df = output[var][r, :, 0]
        country_df = pd.DataFrame(country_df, columns= range(2010, 2051),
                                  index= titles['T2TI'])
        country_df.to_csv(f'../Output/csvs/{var}_{region}.csv', index = True)


# %%

# Plot the data
plt.figure(figsize=(12, 6))
# Variables to change 
var = 'MEWS'
country = 'US'
r = titles['RTI_short']

plt.plot(output['MEWS'][35, 18, 0, :], marker='o')

#%%
# plt.plot(df.index, df['Variable2'], marker='x', label='Variable2')

# # Add title and labels
# plt.title('Time Series Comparison of Variable1 and Variable2')
# plt.xlabel('Date')
# plt.ylabel('Values')
# plt.legend()

# # Rotate the x-axis labels for better readability
# plt.xticks(rotation=45)

# # Show the plot
# plt.grid(True)
# plt.show()
