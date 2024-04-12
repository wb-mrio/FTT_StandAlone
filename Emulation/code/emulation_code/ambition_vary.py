 # -*- coding: utf-8 -*-
"""
Created on Wed Jul 26 15:29:35 2023

Code for varying ambition between S0 and chosen ambitious scenario.

This is then exported

		
MEWT		Technology subsidies, ranging between -1 (full subsidy) and 0.
MEFI		Feed-in tariffs
MEWR		Regulation in GW. When capacity is over regulation, 90% of investments into new capacity is stopped


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

#%% load objects 

sheet_names = ['BCET', 'MEWT', 'MEWR', 'MEFI']

base_scenario = 'S0'
amb_scenario = 'S3'
#master_path = f'Inputs/_Masterfiles/FTT-P/FTT-P-24x70_2021_{base_scenario}.xlsx'
master_path = f'Inputs/_Masterfiles/FTT-P/FTT-P-24x71_2022_{base_scenario}.xlsx'
scenario_levels = pd.read_csv('Emulation/data/scenarios/S3_scenario_levels.csv')

# load reg and backgr var data
input_data = {}

# Loop through the list of sheet names for input data
for sheet_name in sheet_names:
    input_data[sheet_name] = pd.read_excel(master_path, 
                                           sheet_name=sheet_name, 
                                           skiprows=3, 
                                           usecols=lambda column: column not in range(0, 1) and column not in range(22, 26))


# load the comparison between baseline and ambitious scenario 
compare_path = f'Emulation/data/{base_scenario}_{amb_scenario}_comparison.xlsx' # this input will not have varied Background vars

compare_data = {}
# loops through sheets except BCET
for sheet_name in sheet_names[1:]:
    compare_data[sheet_name] = pd.read_excel(compare_path, sheet_name=sheet_name)


# load carbon price data
cp_path = f'Emulation/data/cp_ambit/{amb_scenario}_REPP.csv' # this input will not have varied Background vars, put outside?
cp_df = pd.read_csv(cp_path)




#%%

def uncertainty_inputs(scenario_levels = scenario_levels):
    
    
    scenario_levels = scenario_levels.copy()
    
    # scenarios levels needs to be 1 row of scenarios
    scen_code = scenario_levels['ID']
    
    # load baseline data
    bcet_raw = input_data['BCET']
 
    # Remove placeholders
    bcet = pd.DataFrame()
    for j in range(0, 71*36, 36): # loops through each country
        bcet = pd.concat([bcet, bcet_raw.iloc[j:j+25]]).reset_index(drop = True) # outside function?
    #bcet = bcet.iloc[:,1:] # drop country number col
    
    # implement updates
    solar_update = bcet['Unnamed: 1'] == 'Solar PV'
    bcet.loc[solar_update, 16] = scenario_levels['learning_solar'] # learning rate update
    bcet.loc[solar_update, 9] = scenario_levels['lifetime_solar'] # lifetime update
    bcet.loc[solar_update, 10] = scenario_levels['grid_expansion_lead'] # leadtime update
    onshore_update = bcet['Unnamed: 1'] == 'Onshore'
    bcet.loc[onshore_update, 16] = scenario_levels['learning_wind'] # learning rate update
    bcet.loc[onshore_update, 9] = scenario_levels['lifetime_wind'] # lifetime update
    bcet.loc[onshore_update, 10] = scenario_levels['grid_expansion_lead'] # leadtime update
    offshore_update = bcet['Unnamed: 1'] == 'Offshore'
    bcet.loc[offshore_update, 16] = scenario_levels['learning_wind']  # learning rate update
    bcet.loc[offshore_update, 9] = scenario_levels['lifetime_wind'] # lifetime update
    bcet.loc[offshore_update, 10] = scenario_levels['grid_expansion_lead'] # leadtime update
    
            
    ### COME BACK HERE ######
    global_n_regions =  ['BE', 'DK', 'DE', 'EL', 'ES', 'FR', 'IE', 'IT', 'LX', 
                        'NL', 'AT', 'PT', 'FI', 'SW', 'UK', 'CZ', 'EN', 'CY', 'LV', 'LT',
                        'HU', 'MT', 'PL', 'SI', 'SK', 'BG', 'RO', 'NO', 'CH', 'IS',
                        'HR', 'TR', 'MK', 'US', 'JA', 'CA', 'AU', 'NZ', 'RS', 'RA',
                        'CN'] # China included as pertains to finance - review                

                    
    
    # add discount rate and export
    for i in range(0, len(bcet), 25):
        country = bcet.loc[i, 'Unnamed: 1']
        country_df = bcet.iloc[i:i+25, :].reset_index(drop = True)
        
        if country in global_n_regions:
            country_df.iloc[1:, 17] = scenario_levels['north_discr']
        else:
            country_df.iloc[1:, 17] = scenario_levels['south_discr']
        country_df.iloc[0,0] = '' # delete country tag for export
        
        # add tech numbers
        for index, row in country_df.iloc[1:].iterrows():
            country_df['Unnamed: 1'].iloc[index] = str(index) + ' ' + country_df['Unnamed: 1'].iloc[index]
            
        # Export to input folders
        folder_path = f'Inputs/{scen_code}/FTT-P'
        sheet_out = 'BCET_' + country

        
        # Check if already exists
        if not os.path.exists(folder_path):
            # Create if new
            os.makedirs(folder_path)
            
        country_df.to_csv(folder_path + '/' + f'{sheet_out}.csv', index = False, header = False)
        print(f'Sheet {sheet_out} saved to {folder_path}')

# #%%    
# # discount rate needs adding
# for i in range(0, len(scenario_levels)):
#      uncertainty_inputs(scenario_levels=scenario_levels.iloc[i])

#%% Produces input master sheet for ambition adjusted inputs - reg only

def region_ambition_reg(amb_scenario = 'S3', scenario_levels = scenario_levels, input_data = input_data): # take out S0 and change func name
    
    scenario_levels = scenario_levels.copy()
    amb_scenario = amb_scenario
    new_scen_code = scenario_levels.loc['ID'] 
    
    # List comprehension to filter elements that end with '_reg' and remove suffix
    regions = [country[:-4] for country in list(scenario_levels.index) if country.endswith('_reg')]

    
    europe_plus = ['BE', 'DK', 'DE', 'EL', 'ES','FR','IE','IT','LX','NL','AT',
                   'PT','FI','SW','UK','CZ','EN','CY','LV','LT','HU','MT','PL',
                   'SI','SK','BG','RO','HR', 'NO','CH']
    
    if 'E+' in regions:
            # Add the additional countries to the dictionary with the same value as 'E+'
        regions = regions + europe_plus
        for region in europe_plus:
            scenario_levels.loc[region + '_reg'] = scenario_levels.loc['E+_reg']
        

        
    sheet_names = ['MEWR', 'MEWT', 'MEFI']
    new_sheets = pd.DataFrame()
    
    # create data frame of updates
    for sheet_name in sheet_names:
        var_df = compare_data[sheet_name]
        var_df = var_df[var_df['Scenario'] == amb_scenario].reset_index(drop = True)
        
        for row in var_df.index: 
            if var_df['Country'].iloc[row] in regions:
                country = var_df['Country'].iloc[row]
                
                ambition = scenario_levels[country + '_reg']
            else:
                ambition = scenario_levels['ROW_reg']
            
            meta = var_df.iloc[row, 0:5]
            upper_bound = var_df.iloc[row]
            new_level = (upper_bound[5:] * ambition) # this is currently not GEn, neg numbers
            new_level_meta = pd.concat([meta, new_level])
            new_level_meta = pd.DataFrame(new_level_meta.drop('Scenario')).T
            new_sheets = pd.concat([new_sheets, new_level_meta], axis=0)

    # implement updates to baseline
    for sheet_name in sheet_names:
        master = input_data[sheet_name]
        
        # read in dataframe of changes in new scenario, change name of df1 for better understanding
        sheet_df = new_sheets[new_sheets['Sheet'] == sheet_name].reset_index(drop = True)
        
        
        countries = pd.unique(sheet_df['Country']) # list of countries to loop through
    
        for country in countries:            

            # Country dataframe to merge in
            country_df = sheet_df[sheet_df['Country'] == country].reset_index(drop = True)
            # drop meta data
            country_df = country_df.drop(columns = list(country_df.columns[0:3]))
            country_df = country_df.set_index('Technology')
            
            # update master df, create it and deal with instance of BE
            if country != 'BE':
                master_start = master[master.iloc[:, 0] == country].index[0]
            else: 
                master_start = 0
            master_end = master_start + 25 # all rows until next country
            
            
            master_df = master[master_start:master_end].reset_index(drop = True)
            # Change title of first col to match up with current country_inputs
            master_df.iloc[0, 0] = 'Technology'
            master_df.columns = master_df.iloc[0]
            master_df = master_df[1:]
            master_df = master_df.set_index('Technology')
            
            # Update 
            master_df.update(country_df)
            updated_df = master_df.reset_index()
            updated_df.columns = [''] + list(range(2001, 2101))
            
            # add tech numbers
            for row in list(updated_df.index):
                updated_df.loc[row, ''] = str(row + 1) + ' ' + updated_df.loc[row, '']
                

            # Export to input folders
            folder_path = f'Inputs/{new_scen_code}/FTT-P'
            sheet_out = sheet_name + '_' + country
            
            # Check if already exists
            if not os.path.exists(folder_path):
                # Create if new
                os.makedirs(folder_path)
                
            updated_df.to_csv(folder_path + '/' + f'{sheet_out}.csv', index = False, header = True)
            print(f'Sheet {sheet_out} saved to {folder_path}')
    


## the scenario comparison needs changing for general input


#%% Produces input sheet for ambition adjusted inputs for CP, unlike reg version, sheet is ready to be saved

def region_ambition_cp(scenario_levels = scenario_levels, cp_df = cp_df): # take out S0 and change func name
    
    scenario_levels = scenario_levels.copy()
    new_scen_code = scenario_levels.loc['ID']
    cp_df = cp_df # load carbon price data frame
    
    # List comprehension to filter elements that end with '_reg' and remove suffix
    regions = [country[:-3] for country in list(scenario_levels.index) if country.endswith('_cp')]

    
    europe_plus = ['BE', 'DK', 'DE', 'EL', 'ES','FR','IE','IT','LX','NL','AT',
                   'PT','FI','SW','UK','CZ','EN','CY','LV','LT','HU','MT','PL',
                   'SI','SK','BG','RO','HR', 'NO','CH']
    
    if 'E+' in regions:
            # Add the additional countries to the dictionary with the same value as 'E+'
        regions = regions + europe_plus
        for region in europe_plus:
            scenario_levels.loc[region + '_cp'] = scenario_levels.loc['E+_cp']
  
    # create adjusted cp data frame
    cp_df = cp_df.rename(columns={'Unnamed: 0': ''})
    
    for index, row in cp_df.iterrows():
        country = row['']
        # assign ambition levels
        if country in regions:
            ambition = scenario_levels.loc[country + '_cp'] 
        else:
            ambition = scenario_levels.loc['ROW_cp']
        
        
        # Multiply all values in the row (except country col and 2010) by the ambition value
        cp_df.iloc[index, 2:] = cp_df.iloc[index, 2:] * ambition
        
    # Export to input folders
    folder_path = f'Inputs/{new_scen_code}/FTT-P'
    sheet_out = 'REPP'
    
    # Check if already exists
    if not os.path.exists(folder_path):
        # Create if new
        os.makedirs(folder_path)
        
    cp_df.to_csv(folder_path + '/' + f'{sheet_out}.csv', index = False, header = True)
    print(f'Sheet {sheet_out} saved to {folder_path}')
    

### Do the other inputs in the equations that derive the CP i.e. exchange rate, vary across scenarios??



#%% Example usage
master_path = "Inputs/_MasterFiles/FTT-P/FTT-P-24x71_2022_S0.xlsx"

for i in tqdm(range(0, len(scenario_levels))):
        region_ambition_reg(scenario_levels=scenario_levels.iloc[i])
        region_ambition_cp(scenario_levels = scenario_levels.iloc[i])
        uncertainty_inputs(scenario_levels=scenario_levels.iloc[i])
    

#%% ## Possible developments

# Need to think about MGAMs - value range is a little different
# Also background variables - BCET etc. how do we vary these? Randomly, peturbation?
# load_workbook is really slow and getting sheet names from another way, even manually, would be faster
# change it from scenario compare 
# sort out PK / XX

#### Argument additions:
    # variables of interest?
    



