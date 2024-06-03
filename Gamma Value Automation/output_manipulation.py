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
#%%
os.chdir(r'C:\Users\ib400\OneDrive - University of Exeter\Desktop\PhD\GitHub\FTT_StandAlone')
import SourceCode.support.titles_functions as titles_f

#%% Loading and processing data
titles = titles_f.load_titles()

scenario = 'S0'

# path to output of model runs
output_path = f'Output/Results_{scenario}.pickle'

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
        country_df.to_csv(f'Output/csvs/{var}_{region}.csv', index = True)


# %%
