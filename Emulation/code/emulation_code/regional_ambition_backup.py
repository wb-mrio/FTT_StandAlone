 # -*- coding: utf-8 -*-
"""
Created on Wed Jul 26 15:29:35 2023

Code for varying ambition between S0 and S2.

This can then be exported to country files using 
changed_input_export(compare_path, master_path) from country_inputs.py

		
MEWT		Technology subsidies, ranging between -1 (full subsidy) and 0.
MEFI		Feed-in tariffs
MEWR		Regulation in GW. When capacity is over regulation, 90% of investments into new capacity is stopped
MWKA		Exogenous capacity in GW (kickstart or phase-out policies)


@author: ib400
"""
#%%

import os
import pandas as pd
from openpyxl import load_workbook
from tqdm import tqdm
import random
import numpy as np
from scipy.stats import poisson, binom, uniform, norm, randint
import csv
import copy

os.chdir("C:/Users/ib400/OneDrive - University of Exeter/Documents/GitHub/FTT_StandAlone")


#%% ####### Permutation - use for both reg and CP
# How will it work with the baseline?? Maybe we have enough space to just create them this time
# Vary inputs using ambition_vary.regional_ambition and some sort of permutation

def ambition_generator(countries = ['US', 'CN', 'E+', 'IN', 'BR', 'JA', 'ROW'], num_dicts = 2):
    # List of countries
    countries = countries
    
    # Number of dictionaries you want in your list
    num_dicts = num_dicts
    
    # Create a list of dictionaries
    list_of_dicts = []
    
    # Generate dictionaries with random values
    for _ in range(num_dicts):
        country_data = {}
        for country in countries:
            # Generate a random value between 0 and 1
            value = round(random.uniform(0, 1), 2)

            country_data[country] = value
        list_of_dicts.append(country_data)
        
    return list_of_dicts

#%%

ambition_levels_reg = ambtion_generator(num_dicts=3)


#%%

def uncertainty_generator(base_scenario = 'S0'):
    base_scenario = base_scenario
    master_path = f'Inputs/_Masterfiles/FTT-P/FTT-P-24x70_2021_{base_scenario}.xlsx'
    
    # Monte carlo permutation of key variables
    # Discount rate needs adding
    MC_df = pd.DataFrame(columns = ['learning_solar', 'learning_wind', 'lifetime_solar', 'lifetime_wind', 'grid_expansion_lead'])
    bcet_raw = pd.read_excel(master_path, sheet_name = 'BCET', skiprows=3,
                                 usecols = lambda column: column not in range(22, 26)) # not general yet
    backgr_scen = {}

    # Ranges taken from literature/ expert elicitation
    learning_rate_solar = norm(-0.303, 0.047)         # Learning rate solar
    learning_rate_wind = norm(-0.158, 0.045)             # Learning rate wind
    lifetime_solar = randint(25, 35)                           # Lifetime of solar panel
    lifetime_wind = randint(25, 35)
    grid_expansion_duration = poisson(0.6)               # The lead time of solar
    #gamma = norm(loc=1, scale=0.2)                       # Scaling factor of gamma
    #fuel_costs = norm(loc=1, scale=0.2)                  # Scaling factor of gamma
    
    # Random sampling within ranges
    Nsample = 1
    MC_samples = np.vstack([learning_rate_solar.rvs(Nsample),                    # BCET
                            learning_rate_wind.rvs(Nsample),                     # BCET
                            lifetime_solar.rvs(Nsample),                               # BCET & MEWA
                            lifetime_wind.rvs(Nsample),
                            #gamma.rvs(Nsample),                                  # MGAM # change for big economies
                            #fuel_costs.rvs(Nsample),                             # BCET # need to cahnge indices
                            grid_expansion_duration.rvs(Nsample)+1]).transpose() # BCET & MEWA same for all VREs
    

    # Remove placeholders
    bcet = pd.DataFrame()
    for j in range(0, 71*36, 36):# loops through each country
        bcet = pd.concat([bcet, bcet_raw.iloc[j:j+25]]).reset_index(drop = True) # reset index?? # removes placeholders
        
    
    solar_update = bcet['Unnamed: 1'] == 'Solar PV'
    bcet.loc[solar_update, 16] = MC_samples[0,0] # learning rate update
    bcet.loc[solar_update, 9] = MC_samples[0,2] # lifetime update
    bcet.loc[solar_update, 10] = MC_samples[0,4] # leadtime update
    onshore_update = bcet['Unnamed: 1'] == 'Onshore'
    bcet.loc[onshore_update, 16] = MC_samples[0, 1] # learning rate update
    bcet.loc[onshore_update, 9] = MC_samples[0,3] # lifetime update
    bcet.loc[onshore_update, 10] = MC_samples[0,4] # leadtime update
    offshore_update = bcet['Unnamed: 1'] == 'Offshore'
    bcet.loc[offshore_update, 16] = MC_samples[0, 1] # learning rate update
    bcet.loc[offshore_update, 9] = MC_samples[0,3] # lifetime update
    bcet.loc[offshore_update, 10] = MC_samples[0,4] # leadtime update
    
    # For output, could do this earlier for readability
    MC_samples = pd.DataFrame(MC_samples, columns= MC_df.columns) 
    
    backgr_scen = {'backgr_levels': MC_samples, 'backgr_inputs': bcet}             

    return backgr_scen
# dsicount rate needs adding

#%% Example usage
background_vars = uncertainty_generator()


#%% Produces input master sheet for ambition adjusted inputs - reg only

def region_ambition_reg(regions = {'E+': 1, 'ROW': 0.2}, amb_scenario = 'S3', new_scen_code = 'scen'): # take out S0 and change func name
    
    regions_orig = copy.deepcopy(regions)
    regions = regions
    amb_scenario = amb_scenario
    new_scen_code = new_scen_code
    
    
    europe_plus = ['BE', 'DK', 'DE', 'EL', 'ES','FR','IE','IT','LX','NL','AT',
                   'PT','FI','SW','UK','CZ','EN','CY','LV','LT','HU','MT','PL',
                   'SI','SK','BG','RO','HR', 'NO','CH']
    
    if 'E+' in regions:
            # Add the additional countries to the dictionary with the same value as 'E+'
        for country in europe_plus:
            regions[country] = regions['E+']
    
    
    # load the comparison between baseline and ambitious scenario - can it be external to funciton?
    comparison_path = f'Emulation/data/S0_{amb_scenario}_comparison.xlsx' # this input will not have varied Background vars
    

    sheet_names = ['MEWR', 'MEWT', 'MEFI']
    new_sheets = pd.DataFrame()
    for sheet_name in sheet_names:
        
        var_df = pd.read_excel(comparison_path, sheet_name=sheet_name)
            
        for row in var_df[var_df['Scenario'] == amb_scenario].index: 
            if var_df['Country'].iloc[row] in list(regions.keys()):
                country = var_df['Country'].iloc[row]
                ambition = regions[country]
            else:
                ambition = regions['ROW']
            
            
            meta = var_df.iloc[row, 0:5]
            upper_bound = var_df.iloc[row]
            new_level = (upper_bound[5:] * ambition) # this is currently not GEn, neg numbers
            new_level_meta = pd.concat([meta, new_level])
            new_level_meta = pd.DataFrame(new_level_meta.drop('Scenario')).T
            new_sheets = pd.concat([new_sheets, new_level_meta], axis=0)
            
                
    
    reg_scen = {'reg_levels' : regions_orig, 'reg_inputs' : pd.DataFrame(new_sheets)}
    
    return reg_scen

## the scenario comparison needs changing for general input
#%% Example usage

S3_reg = region_ambition_reg(regions = {'US': 0.5, 'CN': 0.5, 'E+': 1, 'ROW': 0.2}, amb_scenario = 'S3') 

#%% Produces input sheet for ambition adjusted inputs for CP, unlike reg version, sheet is ready to be saved

def region_ambition_cp(regions = {'E+': 1, 'ROW': 0.2}, amb_scenario = 'S3', new_scen_code = None): # take out S0 and change func name
    
    regions_orig = copy.deepcopy(regions)
    regions = regions
    amb_scenario = amb_scenario
    new_scen_code = new_scen_code
    
    europe_plus = ['BE', 'DK', 'DE', 'EL', 'ES','FR','IE','IT','LX','NL','AT',
                   'PT','FI','SW','UK','CZ','EN','CY','LV','LT','HU','MT','PL',
                   'SI','SK','BG','RO','HR', 'NO','CH']
    
    if 'E+' in regions:
            # Add the additional countries to the dictionary with the same value as 'E+'
        for country in europe_plus:
            regions[country] = regions['E+']
  
    # create CP data frame
    cp_path = f'Emulation/data/cp_ambit/{amb_scenario}_REPP.csv' # this input will not have varied Background vars
    cp_df = pd.read_csv(cp_path)
    cp_df = cp_df.rename(columns={'Unnamed: 0': ''})
    
    for index, row in cp_df.iterrows():
        country = row['']
        
        # assign ambition levels
        if country in list(regions.keys()):
            ambition = regions[country] 
        else:
            ambition = regions['ROW']
        
        
        # Multiply all values in the row (except country col and 2010) by the ambition value
        cp_df.iloc[index, 2:] = cp_df.iloc[index, 2:] * ambition
        
    cp_scen = {'cp_levels': regions_orig, 'cp_inputs' : cp_df}
    
    return cp_scen

### Do the other inputs in the equations that derive the CP i.e. exchange rate, vary across scenarios??

#%% Example usage

S3_cp = region_ambition_cp(regions = {'US': 0.5, 'CN': 0.5, 'E+' : 1, 'ROW': 0.2}, amb_scenario = 'S3')




#%% Function that combines regional_ambition functions to create collections of varied input levels
def amb_gen_sheets(reg_levels = {'E+' : 1, 'ROW': 0}, cp_levels = {'E+': 1, 'ROW': 0}, amb_scenario = 'S3',
                   scen_code = 'S3', i = 0, scenarios = scenarios):
    reg_levels = reg_levels
    cp_levels = cp_levels
    amb_scenario = amb_scenario
    scen_code = scen_code
    new_scen_code = f'{scen_code}_{i}'
    base_scenario = 'S0' # make argument?
    
    scenarios = scenarios
    scenario = {}

    
    # create adjusted variables
    adjusted_reg = region_ambition_reg(reg_levels, new_scen_code = new_scen_code)
    adjusted_cp = region_ambition_cp(cp_levels, new_scen_code = new_scen_code)
    adjusted_backvars = uncertainty_generator(base_scenario = base_scenario)
    
    
    # combine to create full scenario
    scenario[new_scen_code] = {'reg_inputs' : adjusted_reg, 'cp_inputs' : adjusted_cp, 'backgr_inputs' :adjusted_backvars}
    
    print(f'Scenario {new_scen_code} created')
    
    # Saving data for recreation of scenarios
    # Specify the file path where you want to save the CSV file
    csv_file = f'Emulation/data/scenarios/{scen_code}_scenario_levels.csv'
    
    # Write the data to the CSV file
    with open(csv_file, 'a', newline='') as file:
        writer = csv.writer(file)
    
        # Write the header row, only needed first time
        #writer.writerow(['Scenario', 'reg_levels', 'cp_levels', 'backgr_levels'])
    
        # Write the data rows
        for scen, levels in scenario.items():
            writer.writerow([scen, adjusted_reg['reg_levels'], adjusted_cp['cp_levels'], adjusted_backvars['backgr_levels']])
    
    print(f'Data for {new_scen_code} saved to {csv_file}')    
    scenarios = scenarios + [scenario]
    

        

    ### can we standardise any of the other variables in the component functions??      

#%% Combine amb_generator and amb_gen_sheets

reg_ambs = ambition_generator(num_dicts=3)
cp_ambs = ambition_generator(num_dicts=3)
scenarios = []

i = 0
for reg, cp in zip(reg_ambs, cp_ambs):
    print('reg levels = ',  reg)
    print('cp levels = ',cp)
    i = i
    amb_gen_sheets(reg_levels=reg, cp_levels=cp, i = i)
    i += 1

#%% Not sure what is gained from this code below, may have been subsumed 
# Function for generating scenario data frames using ambition levels produced by ambition_generator
## and applied to inputs using regional_ambition. These data are then fed into country inputs for production of
## country files

def scenario_generator(ambition_levels = []):
    ambition_levels = ambition_levels
    scenarios_gen = {}
    for i in ambition_levels:
        
        my_dict = i
    
        # Initialize an empty list to store the concatenated key-value pairs
        result_list = []
    
        # Iterate through the dictionary, convert keys and values to strings, and concatenate them
        for key, value in my_dict.items():
            result_list.append(str(key) + "" + str(value))
        
        # Join the list of key-value pairs into one long string, separated by spaces
        result_string = "_".join(result_list)
        
        output = regional_ambition(i, scenarios= ['S0','S3'], new_scen_code= result_string)
    
        scenarios_gen.update(output)
        
    return scenarios_gen

#%%
check = scenario_generator(ambition_levels)





#%% ## Possible developments

# Need to think about MGAMs - value range is a little different
# Also background variables - BCET etc. how do we vary these? Randomly, peturbation?
# load_workbook is really slow and getting sheet names from another way, even manually, would be faster
# change it from scenario compare 

#### Argument additions:
    # variables of interest?
    





