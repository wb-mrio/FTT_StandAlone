# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 12:25:57 2023

code for generating scenarios

@author: ib400
"""
#%%

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

os.chdir("C:/Users/ib400/OneDrive - University of Exeter/Documents/GitHub/FTT_StandAlone")


#%% ####### Permutation - use for both reg and CP
# How will it work with the baseline?? Maybe we have enough space to just create them this time
# Vary inputs using ambition_vary.regional_ambition and some sort of permutation

def ambition_generator(regions = ['E+','US', 'CN', 'IN', 'ROW'], Nscens = 1):
    
    Nscens = Nscens
    # List of countries
    regions = regions
    
    sampler = qmc.LatinHypercube(d=2)

    df = pd.DataFrame()
    for region in regions:
        values = sampler.random(n = Nscens)
        country_vals = pd.DataFrame(values, columns= [region + '_cp', region + '_reg'])
        df = pd.concat([df, country_vals], axis = 1)
        
        
    return df



#%% Uncertainty generator

def uncertainty_generator(Nscens = 1):

    # Random sampling within ranges
    Nscens = Nscens
    
    # Monte carlo permutation of key variables
    MC_df = pd.DataFrame(columns = ['learning_solar', 'learning_wind', 
                                    'lifetime_solar', 'lifetime_wind', 'grid_expansion_lead',
                                    'south_discr', 'north_discr'])

    # Ranges taken from literature/ expert elicitation
    learning_rate_solar = norm(-0.303, 0.047)         # Learning rate solar
    learning_rate_wind = norm(-0.158, 0.045)             # Learning rate wind
    lifetime_solar = randint(25, 35)                           # Lifetime of solar panel
    lifetime_wind = randint(25, 35)
    grid_expansion_duration = randint(1, 3)               # The lead time of solar
    #gamma = norm(loc=1, scale=0.2)                       # Scaling factor of gamma
    #fuel_costs = norm(loc=1, scale=0.2)                  # Scaling factor of gamma
    global_north = []
    global_south = []
    
    #
    for _ in range(Nscens):
        random_numbers = sorted([random.uniform(0.05, 0.2) for _ in range(2)])
        global_south.append(random_numbers[1])
        global_north.append(random_numbers[0])
    
    MC_samples = np.vstack([learning_rate_solar.rvs(Nscens),                    # BCET
                            learning_rate_wind.rvs(Nscens),                     # BCET
                            lifetime_solar.rvs(Nscens),                               # BCET & MEWA
                            lifetime_wind.rvs(Nscens),
                            #gamma.rvs(Nscens),                                  # MGAM # change for big economies
                            #fuel_costs.rvs(Nscens),                             # BCET # need to cahnge indices
                            grid_expansion_duration.rvs(Nscens),
                            global_south,
                            global_north]).transpose() # BCET & MEWA same for all VREs

    # For output, could do this earlier for readability
    MC_samples = pd.DataFrame(MC_samples, columns= MC_df.columns)
    
    
    return MC_samples
    
    


#%% Combine amb_generator and amb_gen_sheets

def scen_generator(Nscens = 5, scen_code = 'S3', regions = ['E+','US', 'CN', 'IN', 'ROW']):
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
    csv_file = f'Emulation/data/scenarios/{scen_code}_scenario_levels.csv'
    scenario_levels.to_csv(csv_file, index = False)
    print(f'Data for {scen_code} scenarios saved to {csv_file}')
    
    return scenario_levels

#%% Example scen_generator, check csv is empty first, this could do with automating
scenario_levels = scen_generator(Nscens=100, regions= ['E+','US', 'CN', 'IN', 'ROW'])

