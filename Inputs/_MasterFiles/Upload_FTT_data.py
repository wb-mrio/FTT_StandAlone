# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 17:10:10 2019

This script extracts all the data from FTT excel sheets in the
"/In/FTTAssumptions/[model]" folders and stores it on the databank of your
choosing (default C databank).

The user can select one or more scenarios to upload from the excel sheet.

@author: MM
"""

import pandas as pd
import numpy as np
import celib
import os
from celib import DB1
from pathlib import Path

"""
Structure of dict:
Model name: [Model abbreviated name, scenarios to read in, excel file]
Scenario 0 = Baseline
Scenario 1 = 2-degree scenario (default)
Scenario 2 = 1.5-degree scenario (default)
ENTER SCENARIO NUMBERS HERE! This will dictate which sheets are read in.
"""
#models = {'FTT-Tr': [[0], 'FTT-Tr_25x70_2021'],
          #'FTT-P': [[0], 'FTT-P-24x71_2022'],
          #'FTT-H': [[0], 'FTT-H-13x71_2023_S0'],
          #'FTT-S': [[0], 'FTT-S-26x70_2021']}

models = {'FTT-H': [[0], 'FTT-H-13x71_2023']}

# models = {'FTT-IH-CHI': [[0], 'FTT-IH-CHI-13x70_2022'],
#           'FTT-IH-FBT': [[0], 'FTT-IH-FBT-13x70_2022'],
#           'FTT-IH-MTM': [[0], 'FTT-IH-MTM-13x70_2022'],
#           'FTT-IH-NMM': [[0], 'FTT-IH-NMM-13x70_2022'],
#           'FTT-IH-OIS': [[0], 'FTT-IH-OIS-13x70_2022'],
# }

#%%
if __name__ == '__main__':
### ----------------------------------------------------------------------- ###
### -------------------------- VARIABLE SETUP ----------------------------- ###
### ----------------------------------------------------------------------- ###
    # Define paths, directories and subfolders
    dirp = os.path.dirname(os.path.realpath(__file__))
    dirp_up = Path(dirp).parents[0]
    dirpdb = os.path.join(dirp, 'databank')

    # Time horizons
    time_horizon_df = pd.read_excel(os.path.join(dirp, 'FTT_variables.xlsx'),
                                    sheet_name='Time_Horizons')
    tl_dict = {}
    for i, var in enumerate(time_horizon_df['Variable name']):
        if time_horizon_df.loc[i, 'Time horizon'] == 'tl_1990':
            tl_dict[var] = list(range(1990, 2100+1))
        elif time_horizon_df.loc[i, 'Time horizon'] == 'tl_2001':
            tl_dict[var] = list(range(2001, 2100+1))
        elif time_horizon_df.loc[i, 'Time horizon'] == 'tl_1918':
            tl_dict[var] = list(range(1918, 2017+1))
        elif time_horizon_df.loc[i, 'Time horizon'] == 'tl_1995':
            tl_dict[var] = list(range(1995, 2100+1))
        elif time_horizon_df.loc[i, 'Time horizon'] == 'tl_2018':
            tl_dict[var] = list(range(2018, 2100+1))

    # Dict to collect errors
    errors = {}

    # Dict to collect all data
    vardict = {}

    # Which variables are uploaded?
    vars_to_upload = {}

    # Loop over all FTT models of interest
    for model in models.keys():
        scenarios = models[model][0]
        errors[model] = []
        vardict[model] = {}

        # Get variable dimensions/attributes
        variables_df = pd.read_excel(os.path.join(dirp, 'FTT_variables.xlsx'),
                                     sheet_name=model,
                                     true_values='y',
                                     false_values='n',
                                     na_values='-')

        for i, var in enumerate(variables_df['Variable name']):
            vardict[model][var] = {}
            vardict[model][var]['Code'] = int(variables_df.loc[i, 'Code'])
            vardict[model][var]['Desc'] = variables_df.loc[i, 'Description']
            vardict[model][var]['Dims'] = [variables_df.loc[i, attr]
                                    for attr in ['RowDim', 'ColDim', '3DDim']
                                    if variables_df.loc[i, attr] not in [0, np.nan]]
            vardict[model][var]['Read in?'] = variables_df.loc[i, 'Read in?']
#            vardict[var]['Scen'] = variables_df.loc[i, 'Scenarios']
            vardict[model][var]['Data'] = {}
            

        # Get model classifications
        dims = list(pd.concat([variables_df['RowDim'], variables_df['ColDim'], variables_df['3DDim']]))
        dims = list(set([dim for dim in dims if dim not in ['TIME', np.nan, 0]]))
        dims = {dim: None for dim in dims}
        with DB1(os.path.join(dirpdb, 'U.db1')) as db1:
            for dim in dims:
                dims[dim] = db1[dim]
#%%
### ----------------------------------------------------------------------- ###
### ---------------------------- EXTRACT DATA ----------------------------- ###
### ----------------------------------------------------------------------- ###
        # Define which sheets to load
        vars_to_upload[model] = [var for var in vardict[model] if vardict[model][var]['Read in?']]
#        scen_vars = [var for var in vardict if vardict[var]['Scen']]

        sheets = ['Titles'] + vars_to_upload[model]

        for scen in scenarios:

            out_dir = os.path.join(dirp_up, 'S{}'.format(scen), model)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)


            # Check whether the excel files exist
            raw_f = models[model][1]
            raw_p = os.path.join(dirp, model, '{}_S{}.xlsx'.format(raw_f, scen))
            if not os.path.exists(raw_p):
                msg = "{} does not exists. {} variables will not be uploaded".format(raw_f, model)
                print(msg)
                continue
            # Tell the user that the file is being read in.
            msg = "Extracting {} variables of scenario {} from the excelsheets".format(model, scen)
            print(msg)
            
            #Defining relevant rows
            #class_titles = pd.read_excel('classification_titles.xlsx', sheet_name = 'HTTI')
            #relevant_rows = set(class_titles.iloc[:, 0])

            # Load sheets
            raw_data = pd.read_excel(raw_p, sheet_name=sheets, header=None)
            
            # import re
        
            # filtered_raw_data = {}

            # Define the pattern to match 'placeholder' as a separate word
            # word_to_filter = r'\bPlaceholder\b'
            
            # Iterate through the original raw_data dictionary
            # for key, data in raw_data.items():
                # if not any(re.search(word_to_filter, str(cell)) for cell in data):
                    # If the pattern is not found, add the data to the filtered_raw_data dictionary
                    # filtered_raw_data[key] = data
                    
                    #raw_data = filtered_raw_data
                    
                    #print(raw_data)
            
            # filtered_raw_data now contains the filtered data without rows containing 'placeholder' as a separate word
            

            # Get titles from the Titles sheet in the excel file
            raw_titles = raw_data['Titles']
            ftt_titles = {}
            for col in range(1, raw_titles.shape[1], 2):
                var = raw_titles.iloc[0, col]
                titles = list(raw_titles.iloc[:, col].dropna())[1:]
                ftt_titles[var] = titles

            # Extract data & save to relevant variable
            row_start = 5
            regs = dims['RSHORTTI']

            ## Read in sheet by sheet
            ci = 2
            for i, var in enumerate(vars_to_upload[model]):
                ndims = len(vardict[model][var]['Dims'])
                rdim = len(dims[vardict[model][var]['Dims'][0]])
                r_ttle = dims[vardict[model][var]['Dims'][0]]
                #r_ttle = [r for r in r_ttle if r in relevant_rows]
                if len(vardict[model][var]['Dims']) == 1:
                    cdim = 1
                    c_ttle = ['NA']
                elif vardict[model][var]['Dims'][1] != 'TIME':
                    cdim = len(dims[vardict[model][var]['Dims'][1]])
                    c_ttle = dims[vardict[model][var]['Dims'][1]]
                else:
                    cdim = len(tl_dict[var])
                    c_ttle = tl_dict[var]
                excel_dim = len(ftt_titles[vardict[model][var]['Dims'][0]])
                cf = ci + cdim
                sep = 1 + excel_dim - rdim
                vardict[model][var]['Data'][scen] = {}
                sheet_name = var
                if ndims == 3:
                    vardict[model][var]['Data'][scen] = {}
                    for i, reg in enumerate(regs):
                        ri = row_start + i*(rdim + sep)
                        rf = ri + rdim
                        data = raw_data[sheet_name].iloc[ri:rf, ci:cf]
                        vardict[model][var]['Data'][scen][reg] = np.array(data.astype(np.float32))

                        out_fn = os.path.join(out_dir, "{}_{}.csv".format(var, reg))
                        df = pd.DataFrame(data.values, index=r_ttle, columns=c_ttle)
                        mask = ~df.index.to_series().astype(str).str.contains(r'\bundefined\b', case=False)
                        df = df[mask]
                        # print(df)
                        df.to_csv(out_fn)

                elif ndims == 2:
                    ri = row_start
                    rf = ri + rdim
                    data = raw_data[sheet_name].iloc[ri:rf, ci:cf]
                    vardict[model][var]['Data'][scen] = np.array(data.astype(np.float32))

                    out_fn = os.path.join(out_dir, "{}.csv".format(var))
                    df = pd.DataFrame(data.values, index=r_ttle, columns=c_ttle)
                    mask = ~df.index.to_series().astype(str).str.contains(r'\bundefined\b', case=False)
                    df = df[mask]
                    # print(df)
                    df.to_csv(out_fn)

                elif ndims == 1:
                    ri = row_start
                    rf = ri + rdim
                    data = raw_data[sheet_name].iloc[ri:rf, ci:cf]
                    vardict[model][var]['Data'][scen] = np.array(data.astype(np.float32))

                    out_fn = os.path.join(out_dir, "{}.csv".format(var))
                    df = pd.DataFrame(data.values, index=r_ttle, columns=c_ttle)
                    mask = ~df.index.to_series().astype(str).str.contains(r'\bundefined\b', case=False)
                    df = df[mask]
                    df.to_csv(out_fn)

                    msg = "Data for {} saved to CSV. Model: {}".format(var, model)
                    print(msg)

                    # Only return gamma sheets for the first scenario
    if scen != "0":
        pass
    else:
        var = "HGAM"
        sheet_name = 'BHTC'
        bhtc = pd.read_excel(models, sheet_name=sheet_name)
        gamma_1D = bhtc[12]
        col_names = list(range(2014, 2101))
        # Make data 2D with np.tile
        data = pd.DataFrame(np.tile(gamma_1D.values.T, (len(col_names), 1)).T)
     
        # Add column names    
        data.columns = col_names
        out_fn = os.path.join(out_dir, "{}_{}.csv".format(var, reg))
        df = pd.DataFrame(data.values, index=dims["HTTI"], columns=col_names)
        mask = ~df.index.to_series().astype(str).str.contains(r'\bundefined\b', case=False)
        df = df[mask]
        df.to_csv(out_fn)
