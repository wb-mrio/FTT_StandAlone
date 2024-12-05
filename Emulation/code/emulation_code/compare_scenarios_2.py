# -*- coding: utf-8 -*-
"""
Created on Wed Apr 10 16:36:26 2024

Script for converting masterfiles into dataframes for comparison between scenarios

Returns:
    - Saved output_workbooks with sheets for each variable
    - Data stored in wide format with country and scenario as cat var

Possible developments

### This code needs streamlining to be just a function that can be called in the run file
### Remove placeholders and clean up wrangle, too inefficient
### master.columns = ['Technology'] + list(master.columns[1:]) # do we need to rename, can we search by index later??
### The interim dataframes don't have the sheet names associated'

Script for comparing masterfile input sheets. Useful for checking for hidden changes when
performin model update.

Uses a adapted version of some emulation code, this should be generalised and put
into Sourcecode/support

@author: ib400
"""
# Load packages

import pandas as pd
import numpy as np
import os
import sys


# Get the absolute path of the current script
current_script_path = os.path.abspath(__file__)

# Get the absolute path of the root directory (assuming the root directory is 3 levels up from the current script)
root_directory_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_script_path))))

# Path to the 'support' directory
emulation_directory_path = os.path.join(root_directory_path, 'Emulation', 'code', 'emulation_code')

# Add the 'support' directory to sys.path if it's not already there
if emulation_directory_path not in sys.path:
    sys.path.append(emulation_directory_path)


os.chdir(root_directory_path)


#%% 


# Change depending on scenario
#scen = 'S2' ## this needs sorting and the scens need to be generalised
scenario_list = ['S0', 'S3']

# create dictionaries to store input files
# dictionaries used for generalisation and multiple scenarios
file_paths = {}

# Load the Excel workbook
for scen in scenario_list:
    file_paths[scen] = os.path.join(root_directory_path, f"Inputs\\_Masterfiles\\FTT-P\\FTT-P-24x71_2024_{scen}.xlsx")


# Dictionary to store DataFrames with variable names based on scenarios
dataframes = {}

for scen in scenario_list:
    dataframes[f"df_{scen}"] = []

# Specify the sheet names to process
sheets_to_process = ['BCET', 'MEWT', 'MEWR', 'MEFI']  


#%% ## take input masterfiles and wrangle to remove unneccessary info. 

# Iterate over the desired sheets and apply the transformations
for scen in scenario_list:
    dataframes[f"df_{scen}"] = {}
    for sheet_name in sheets_to_process:
        
        # Load the sheet into a DataFrame      
        df = pd.read_excel(file_paths[scen],sheet_name=sheet_name, 
                           skiprows=3, usecols=lambda column:  column not in range(22, 26))
        
        
        # Extract every 36th row from the column
        numb_col = df[0].iloc[::36].reset_index(drop=True)
        country_col = df.iloc[:, 1].iloc[::36].reset_index(drop=True)
        #country_col = df['Unnamed: 1'].iloc[::36].reset_index(drop=True)
        
        # Repeat the extracted values for the next 36 rows
        numb_col = numb_col.repeat(36).reset_index(drop=True)
        country_col = country_col.repeat(36).reset_index(drop=True)
        
        # Insert the new column as the first 2 columns in the DataFrame
        df[0] = numb_col
        df.insert(1, 'Country', country_col)
        
        # Delete the rows that were used to create the new column
        rows_to_delete = df.index[36::36]
        df = df.drop(rows_to_delete)
        
        # Set the first row as column names
        df.columns = df.iloc[0]
        df.columns.values[0:3] = ['Code', 'Country', 'Technology']
        
        # Delete the first row from the DataFrame
        df = df.iloc[1:].reset_index(drop=True)
        
        dataframes[f"df_{scen}"][sheet_name] = df
        

#%% Create new excels for inspection

sheets_to_output = sheets_to_process  # Add the desired sheet names here

for scen in scenario_list:
    # Create a new Excel writer object
    #with pd.ExcelWriter(f'Emulation/data/output_workbook_{scen}_24x71_2022.xlsx') as writer:
    with pd.ExcelWriter(f'Emulation/data/comparisons/output_workbook_{scen}.xlsx',  engine='openpyxl') as writer:

        # Iterate through the sheet names and output list
        for sheet_name in dataframes[f"df_{scen}"]:
            
            print(f'{sheet_name} for scenario {scen} saved')
            # Create a new DataFrame from the output
            df = pd.DataFrame(dataframes[f"df_{scen}"][sheet_name])
            
            # Write the DataFrame to a new sheet in the output workbook
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    
#%%

def compare_scenarios(scen_base, scen_compare, keep_equal = False):
    
    scen_base = scen_base
    scen_compare = scen_compare
    keep_equal = keep_equal
    
    # create file names
    baseline = f'Emulation/data/comparisons/output_workbook_{scen_base}.xlsx'
    comparison = f'Emulation/data/comparisons/output_workbook_{scen_compare}.xlsx'
    

    # Get the sheet names from both workbooks
    sheet_names = sheets_to_process
    
    
    # Initialize an empty DataFrame to store the changed rows
    changed_rows = {}
    
    for sheet_name in sheet_names:
        changed_rows[sheet_name] = []
        
        

        # Read the sheets from both workbooks into DataFrames
        df1 = pd.read_excel(baseline, sheet_name=sheet_name)
        df2 = pd.read_excel(comparison, sheet_name=sheet_name)

        # Compare the DataFrames and find the changed rows
        # other arguments available for different kinds of input
        print(f'comparing {sheet_name} between {scen_base} and {scen_compare}')
        diff = df1.compare(df2, align_axis = 'index',
                           result_names = (f'{scen_base}', f'{scen_compare}'), keep_equal = keep_equal) #(scen_base, scen_compare)) # names can be automated

        
        if not diff.empty:
            # Make scenario a variable
            diff = diff.reset_index(level=1)
            diff.columns = ['Scenario'] + list(diff.columns[1:])
            # add in metadata
            diff.insert(1, 'Sheet', sheet_name)
            diff.insert(2,'Code', df1['Code'])
            if 'Country' not in diff.columns:
                diff.insert(3, 'Country', df1['Country'])
            diff.insert(4, 'Technology', df1['Technology'])
            #enter the two rows below if the chopped index is desired
            # diff = diff.reset_index()
            # diff.columns = ['Row'] + list(diff.columns[1:])
            
            changed_rows[sheet_name] = diff


    return changed_rows

#%% 

def export_compare(compare_output, output_base):
    
    output_file = output_base
    with pd.ExcelWriter(output_file) as writer:
        # Loop through the keys of the dictionary
        for sheet_name in compare_output.keys():
            # Retrieve the DataFrame from the dictionary
            df = compare_output[sheet_name]
            if type(df) != list:
                df.to_excel(writer, sheet_name=sheet_name, index=False)


#%% Action comparison and saved to Emulation data

comp_0_3 = compare_scenarios('S0', 'S3')
export_compare(comp_0_3, "Emulation/data/comparisons/S0_S3_comparison.xlsx")

# %%
