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

os.chdir("C:/Users/ib400/OneDrive - University of Exeter/Documents/GitHub/FTT_StandAlone")

#%%

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


### Baseline

# path to output of model runs
output_path = f'Output/Results_S0_core.pickle'

# Open the pickle file in binary mode and load its content
with open(output_path, 'rb') as file:
    # Use pickle.load() to load the content into a dictionary
    output = pickle.load(file)


mcoc = output['MCOC']
mcocx = output['MCOCX']

mcoc_us  = mcoc[36, :, 0, :]
mcocx_us = mcocx[36, :, 0, :]
