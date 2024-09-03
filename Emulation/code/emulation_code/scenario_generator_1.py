# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 12:25:57 2023

This script is for generating scenarios between a baseline and an ambitious scenario.
The variables to be varied can be altered as well as the countries for which ambition is varied.
Sources for the parameter ranges are provided in the comments.

Possible developments:
uncertainty_generator() currently has the variables hardcoded, could be made more flexible
by passing a dictionary of variables and their ranges.

@author: ib400
"""
#%%

# Load libraries
import os
import pandas as pd
from openpyxl import load_workbook
from tqdm import tqdm
import random
import numpy as np
from scipy.stats import poisson, binom, uniform, norm, randint, qmc
import csv
import copy
import matplotlib.pyplot as plt
import sys
from pyDOE import lhs

# Get the absolute path of the current script
current_script_path = os.path.abspath(__file__)

# Get the absolute path of the root directory (assuming the root directory is 3 levels up from the current script)
root_directory_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_script_path))))

# Path to the 'support' directory
emulation_directory_path = os.path.join(root_directory_path, 'Emulation', 'code', 'emulation_code')

# Add the 'support' directory to sys.path if it's not already there
if emulation_directory_path not in sys.path:
    sys.path.append(emulation_directory_path)


#%% ####### Generate ambition levels - use for both regulation and carbon pricing

def ambition_generator(regions = ['EA','US', 'CN', 'IN', 'BR', 'RGS', 'RGN'], Nscens = 1):
    
    # Number of scenarios
    Nscens = Nscens
    # List of countries
    regions = regions
    
    # Latin hypercube sampling over 2 dimensions
    sampler = qmc.LatinHypercube(d=3)

    # Generate random values for each region evenly spaced
    df = pd.DataFrame()
    for region in regions:
        values = sampler.random(n = Nscens)
        values = np.round(values, 2)  # Round values to 3 decimal places
        country_vals = pd.DataFrame(values, columns= [region + '_cp', region + '_phase', region + '_price'])
        df = pd.concat([df, country_vals], axis = 1)
        
        
    return df



#%% Uncertainty generator - currently hardcoded, could be passed but need numtype e.g. integer

def uncertainty_generator(Nscens = 1):
    # Random sampling within ranges
    Nscens = Nscens
    
    # LHS sampling of key variables
    LHS_df = pd.DataFrame(columns = ['learning_solar', 'learning_wind', 
                                    'lifetime_solar', 'lifetime_wind', 
                                    'lead_offshore', 'lead_onshore', 'lead_solar',
                                    'south_discr', 'north_discr', 'elec_demand',
                                    'gas_price', 'coal_price', 'tech_potential',
                                    ])

    # Define the ranges for each variable
    # This could be taken out of the function for generalisation
    ranges = {'learning_solar': (-0.473, -0.165), # mean = 0.319 +/- (1x standard error + noise) - Way et al. 2022
              'learning_wind': (-0.3, -0.088), # mean 0.194 +/- (1x standard error + noise) - Way et al. 2022
              'lifetime_solar': (20, 35), # Krey et al. 2019
              'lifetime_wind': (20, 35), # Krey et al. 2019
              'lead_offshore': (3, 8), # Source?
              'lead_onshore': (1, 4), # Source?
              'lead_solar': (1, 4), # Source?
              'south_discr': (0.05, 0.25),
              'north_discr': (0.05, 0.25),
              'elec_demand': (0, 1),
              'gas_price': (0, 1),
              'coal_price': (0, 1),
              'tech_potential': (0, 1),
              }
    
    # Perform LHS for each variable
    for var, (lower, upper) in ranges.items():
        if var in ['lifetime_solar', 'lifetime_wind', 'lead_offshore', 'lead_onshore', 'lead_solar']:
            samples = lhs(1, samples=Nscens)
            scaled_samples = lower + np.round(samples * (upper - lower))
        else:
            samples = lhs(1, samples=Nscens)
            scaled_samples = lower + samples * (upper - lower)
            scaled_samples = np.round(scaled_samples, 2)  # Round values to 3 decimal places

        LHS_df[var] = scaled_samples.flatten()
    
    return LHS_df
    
    


#%% Combine amb_generator and uncertainty_generator to create scenarios, LHS STRUCTURE INCORPORATED?

def scen_generator(Nscens, regions, scen_code = 'S3'):
    Nscens = Nscens
    regions = regions
    
    ids = pd.DataFrame(columns = ['ID'])
    scenario_ids = [f'{scen_code}_{j}' for j in range(Nscens)]
    ids['ID'] = pd.Series(scenario_ids)
    
    ambition_levels = ambition_generator(regions = regions, Nscens = Nscens)
    backgr_levels = uncertainty_generator(Nscens = Nscens)
    
    scenario_levels = pd.concat([ids, ambition_levels, backgr_levels], axis = 1)
    
    # Saving data for recreation of scenarios
    # Specify the file path where you want to save the CSV file
    csv_file = os.path.join(root_directory_path, 'Emulation', 'data', 'scenarios', f'{scen_code}_scenario_levels.csv')
    scenario_levels.to_csv(csv_file, index = False)
    print(f'Data for {scen_code} scenarios saved to {csv_file}')
    
    return scenario_levels

#%% Example scen_generator, check csv is empty first, this could do with automating
scenario_levels = scen_generator(Nscens=401, regions = ['EA','US', 'CN', 'IN', 'BR', 'RGS', 'RGN'])


# %%
