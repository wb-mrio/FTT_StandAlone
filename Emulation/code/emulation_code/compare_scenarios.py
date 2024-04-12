# -*- coding: utf-8 -*-
"""
Created on Wed Jul 19 11:29:12 2023

Functions for comparing 2 scenarios and then exporting the results:
    
    compare_scenarios(scen_base, scen_compare)
    export_compare(compare_output, output_file)

Output is an excel workbook with sheets that show the differences for those 
inputs across the 2 scenarios. 

Paths to workbooks may need adjusting depending on masterfile used
The masterfile cost matrix for the new S2 differs from S0 which is incorrect,
use only the baseline

### Developments

    # Colour code the different scenarios, not sure if possible in python
    # Freeze panes automatically
    # Do something with missing values
    # Change so that baseline values are included for all cells in comparison and 
    # colour for base and comparison (red/green)
    # Needs adapting so that scenarios can be read in from different sources, so 
    # not just a comparison workook
    # need to always have the original value in the baseline so we know what is was when
    # it is the same as the compare

@author: ib400
"""
import os
import pandas as pd
from openpyxl import load_workbook

os.chdir("C:/Users/ib400/OneDrive - University of Exeter/Documents/GitHub/FTT_StandAlone")


#%%

def compare_scenarios(scen_base, scen_compare):
    # create file names
    baseline = f'Emulation/data/output_workbook_{scen_base}_24x71_2022.xlsx'
    comparison = f'Emulation/data/output_workbook_{scen_compare}_24x71_2022.xlsx'
    
    # Load the workbooks
    wb1 = load_workbook(filename= baseline)
    # Get the sheet names from both workbooks
    sheet_names = ['MEWT', 'MEWR', 'MEFI']

    # Initialize an empty DataFrame to store the changed rows
    changed_rows = {}


    for sheet_name in sheet_names:
        changed_rows[sheet_name] = []
        
        # Read the sheets from both workbooks into DataFrames
        df1 = pd.read_excel(baseline, sheet_name=sheet_name)
        df2 = pd.read_excel(comparison, sheet_name=sheet_name)

        # Compare the DataFrames and find the changed rows
        # other arguments available for different kinds of input
        diff = df1.compare(df2, align_axis = 'index',
                           result_names = (scen_base, scen_compare)) # names can be automated

        
        if not diff.empty:
            # Make scenario a variable
            diff = diff.reset_index(level=1)
            diff.columns = ['Scenario'] + list(diff.columns[1:])
            # add in metadata
            diff.insert(1, 'Sheet', sheet_name)
            diff.insert(2,'Code', df1['Code'])
            diff.insert(3, 'Country', df1['Country'])
            diff.insert(4, 'Technology', df1['Technology'])
            #enter the two rows below if the chopped index is desired
            # diff = diff.reset_index()
            # diff.columns = ['Row'] + list(diff.columns[1:])
            
            changed_rows[sheet_name] = diff


    return changed_rows


#%% ## Example usage

def export_compare(compare_output, output_file):
   
    with pd.ExcelWriter(output_file) as writer:
        # Loop through the keys of the dictionary
        for sheet_name in compare_output.keys():
            # Retrieve the DataFrame from the dictionary
            df = compare_output[sheet_name]
            if type(df) != list:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    writer.close()


#%%
# Example usage
comparison_output = compare_scenarios('S0', 'S3')
export_compare(comparison_output,'Emulation/data/S0_S3_comparison.xlsx')






