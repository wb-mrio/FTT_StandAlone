# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 17:10:10 2019

This script extracts all the data from FTT excel sheets in the
"/In/FTTAssumptions/[model]" folders and saves them in separate csv files.

The user can select one or more scenarios to convert from the excel sheet:
    1. If running this code as a script, set the input files in the final lines of the code
    2. If the script is run at the start of the model run, it will automatically
    detect which files to convert, based on available csv files and whether
    the masterfile is newer than the csv files. 

@author: MM and Femke Nijsse
"""

from pathlib import Path
import os
import sys

import pandas as pd
import numpy as np
import datetime

# Get the absolute path of the current script
current_script_path = os.path.abspath(__file__)

# Get the absolute path of the root directory
root_directory_path = os.path.dirname(os.path.dirname(os.path.dirname(current_script_path)))

# Path to the 'support' directory
support_directory_path = os.path.join(root_directory_path, 'SourceCode', 'support')

# Add the 'support' directory to sys.path if it's not already there
if support_directory_path not in sys.path:
    sys.path.append(support_directory_path)

from titles_functions import load_titles

#%% Function definitions

def csv_exists(file_path):
    """Check if a CSV file already exists."""
    return os.path.isfile(file_path)


def read_data(models, model, dir_masterfiles, scen, sheets):
    """
    Read the masterfiles
    
    Returns:
        raw_data: the dataframe with all the excel data"""
    # Check whether the excel files exist
    raw_f = models[model][1]
    raw_p = os.path.join(dir_masterfiles, model, f'{raw_f}_S{scen}.xlsx')
    if not os.path.exists(raw_p):
        print(f"{raw_f} does not exists at {raw_p}. No csv files will be created for {model} variables")
        return None

    # Tell the user that the file is being read in.
    print(f"Extracting {model} variables of scenario {scen} from the excelsheets")

    # Load sheets
    raw_data = pd.read_excel(raw_p, sheet_name=sheets, header=None)
    return raw_data


def extract_data(raw_data, sheet_name, row_start, rdim, ci, cf):
    """Extract a slice of data and convert it to a numpy array."""
    ri = row_start
    rf = ri + rdim
    data = raw_data[sheet_name].iloc[ri:rf, ci:cf]
    return data


def get_sheets_to_convert(var_dict, model, scen):
    """ Get all the variables to convert to CSV files
    There are two options:
        1. Convert all variables from excel sheet (for S0)
        2. Convert only policy variables (for other scenarios). 
    You can change which variables are in all scenarios in the FTT_variables file, column Scenario
    """
    
    # In the baseline scenario, all variables are converted
    if scen == 0:
        vars_to_convert = [var for var in var_dict[model] if var_dict[model][var]['Read in?']]
    
    # In the other scenarios, only policy variables are converted
    else:
        vars_to_convert = [var for var in var_dict[model] if \
                   (var_dict[model][var]['Scenario'] == "All" and var_dict[model][var]['Read in?'])]

    sheets = ['Titles'] + vars_to_convert

    return vars_to_convert, sheets

def are_csvs_older_than_masterfiles(vars_to_convert, out_dir, models, \
                                      model, scen, dir_masterfiles):
    """
    Find which files were last modified. If masterfile is newest then newest
    csv files, overwrite all csv files.
    
    Returns true if the csvs need updating and are older
    """
    
    def find_last_time_csv_modified(vars_to_convert, out_dir):
        """
        For a given module and scenario, compares the most recent date
        a csv file was last updated
        """
        # Take old time to compare to
        last_time_modified = datetime.datetime(2021, 1, 1)
        
        for var in vars_to_convert:
            out_fn = os.path.join(out_dir, f"{var}.csv")
            out_fn_reg = os.path.join(out_dir, f"{var}_BE.csv")
            if csv_exists(out_fn):
                time_modified = os.path.getmtime(out_fn)
            elif csv_exists(out_fn_reg):
                time_modified = os.path.getmtime(out_fn_reg)
            else:
                print(f"var does not exist: {var}")
                print(f"vars_to_convert: {vars_to_convert}")
                continue
            
            time_modified =  datetime.datetime.fromtimestamp(time_modified)
            if time_modified > last_time_modified:
                last_time_modified = time_modified
        
        return last_time_modified
    
    def find_last_time_masterfile_modified(models, model, scen, dir_masterfiles):
        """
        For a given module and scenario, compares the most recent date
        a csv file was last updated
        """
        # Check whether the excel files exist
        raw_f = models[model][1]
        raw_p = os.path.join(dir_masterfiles, model, f'{raw_f}_S{scen}.xlsx')
        time_modified = os.path.getmtime(raw_p)
        time_modified = datetime.datetime.fromtimestamp(time_modified)
        return time_modified
    
    csv_time_mod = find_last_time_csv_modified(vars_to_convert[model], out_dir)
    master_time_mod = find_last_time_masterfile_modified(models, model, scen, dir_masterfiles)
    
    if master_time_mod > csv_time_mod:
        print("There are new updates to the Masterfile, so csv files will be updated")
    return master_time_mod > csv_time_mod

def get_remaining_variables(vars_to_convert, out_dir, model, \
                            var_dict, gamma_options, overwrite_existing_csvs):
    """
    Remove variables from the to-convert list if:
        a) We do not overwrite existing csv and
        b) They already exist
    
    Returns:
        * the remaining variables to convert
        * the gamma user input (unchanged if not applicable)
    """
    
    # Keep all variables (possibly excl gamma) in the to-convert list if:
    if overwrite_existing_csvs:
        
        for var in vars_to_convert:

            # Check if the user wants to overwrite gamma values
            if var_dict[model][var]["Conversion?"] == "GAMMA" or var=="MGAM":
                gamma_options["Overwrite user input"] = \
                    gamma_input_on_overwrite(out_dir, var, gamma_options)
        
        return vars_to_convert, gamma_options
    
    # Remove variables from list if we do not overwrite AND they already exist
    vars_to_convert_remaining = []
    for var in vars_to_convert:     
        out_fn = os.path.join(out_dir, f"{var}.csv")
        out_fn_reg = os.path.join(out_dir, f"{var}_BE.csv")
        
        exists = (csv_exists(out_fn) or csv_exists(out_fn_reg))
                
        if not exists:
            vars_to_convert_remaining.append(var)
    
    return vars_to_convert_remaining, gamma_options


def gamma_input_on_overwrite(out_dir, var, gamma_options):
    """
    When the script is run as a script, and the gamma csv files already exist,
    confirm with the user if you want to overwrite, given that
    the user may not want to lose their calibrated gamma values 
    """
    
    costvar_to_gam_dict = {"MGAM": "MGAM", "BTTC": "TGAM", "BHTC": "HGAM", "ZCET": "ZGAM"}
    var_gamma = costvar_to_gam_dict[var]
    out_fn = os.path.join(out_dir, f"{var_gamma}_BE.csv")
    
    # Break if no user input is required
    if not gamma_options["Ask user input"]:
        return None

    if gamma_options["Overwrite user input"] is None:
        if csv_exists(out_fn) and var_gamma.endswith('GAM'):
            file_string = out_fn.split('Inputs', 1)[-1].replace("BE", "XX")
            proceed = input(f"CSV files {file_string} already exist. Do you want to overwrite them? (y/n) ")
            if proceed.lower() != 'y':
                print("Skipping...")
                return "skip"
            
            print("Overwriting...")
            return "overwrite"

def set_up_rows(model, var, var_dict, dims):
    """Setting up the size of the rows, and the name of the rows"""

    try:
        rdim = len(dims[var_dict[model][var]['Dims'][0]])
    except KeyError:
        print(f'model is {model}')
        print(f'var is {var}')
    row_title = dims[var_dict[model][var]['Dims'][0]]

    return rdim, row_title

def set_up_cols(model, var, var_dict, dims, timeline_dict):
    """Set up the size and name of a column."""
    
    dimensions = var_dict[model][var]['Dims']
    # If there is only a single column / scalar
    if len(dimensions) == 1:
        cdim = 1
        col_title = ['NA']
    # If there are multiple columns and the column isn' time
    elif dimensions[1] != 'TIME':
        cdim = len(dims[var_dict[model][var]['Dims'][1]])
        col_title = dims[var_dict[model][var]['Dims'][1]]
    # If the second dimension is time
    else:
        cdim = len(timeline_dict[var])
        col_title = timeline_dict.get(var, [])
        if not col_title:
            print(f"KeyError: {var} not found in timeline_dict.")

    return cdim, col_title


def write_to_csv(data, row_title, col_title, var, out_dir, reg=None):
    """Write the variables to a csv file, or to multiple csv files for 3D vars"""
    if reg:
        out_fn = os.path.join(out_dir, f"{var}_{reg}.csv")
    else:
        out_fn = os.path.join(out_dir, f"{var}.csv")
    
    df = pd.DataFrame(data.values, index=row_title, columns=col_title)
    df.to_csv(out_fn)


def costs_to_gam(data, var, reg, timeline_dict, dims, out_dir):
    """
    In Tr, H and Fr, gamma values are not saved separately, but instead
    part of the cost variable. Here, those values are extracted to ensure the
    gamma values are defined for each year.
    """

    costvar_to_gam_dict = {"BTTC": "TGAM", "BHTC": "HGAM", "ZCET": "ZGAM"}
    gamma_index = {"BTTC": 14, "BHTC": 13, "ZCET": 13}
    gamma_row_titles = {"BTTC": "VTTI", "BHTC": "HTTI", "ZCET": "FTTI"}
    gamma_var = costvar_to_gam_dict[var]
    gamma_1D = data[gamma_index[var]]
    col_names = timeline_dict[gamma_var]

    # Make data 2D with np.tile
    data = pd.DataFrame(np.tile(gamma_1D.values.T, (len(col_names), 1)).T)

    # Add column names
    data.columns = col_names
    row_title = dims[gamma_row_titles[var]]
    col_title = col_names
    
    write_to_csv(data, row_title, col_title, gamma_var, out_dir, reg=reg)

def convert_1D_var_to_timeline(data, var, row_title, out_dir, timeline_dict):
    """ Some variables (e.g. TEWW, MEWW), are 1D in the excel sheets. 
    However, in the model, these variables change over time, 
    and we store this data. Therefore, the csv files should have a time dimension
    """

    # Make data 2D with np.tile
    col_names = timeline_dict[var]
    data = pd.DataFrame(np.tile(data.values.T, (len(col_names), 1)).T)

    # Add column names
    data.columns = col_names

    write_to_csv(data, row_title, col_names, var, out_dir)


# Core functions for the main programme
def directories_setup():
    """ Set up directory masterfile, the directory above it, and the databank directory"""
    dir_file = os.path.dirname(os.path.realpath(__file__))
    dir_root = Path(dir_file).parents[1] 
    dir_inputs = os.path.join(dir_root, "Inputs")  
    dir_masterfiles = os.path.join(dir_root, "Inputs", "_MasterFiles")
    # Classifications

    titles_file = 'classification_titles.xlsx'
    # Check that classification titles workbook exists
    titles_path = os.path.join(dir_root, 'Utilities', 'titles', titles_file)
    
    if not os.path.isfile(titles_path):
        print(f'Classification titles file not found at {titles_path}.')
    
    return dir_inputs, dir_masterfiles, titles_path


def variable_setup(dir_masterfiles, models):
    """Set up the various containers and metadata for variables:
        variables_df_dict, var_dict, vars_to_convert, scenarios, timeline_dict
    """
    # Time horizons, as defined in the Time Horizons sheet
    time_horizon_df = pd.read_excel(os.path.join(dir_masterfiles, 'FTT_variables.xlsx'),
                                    sheet_name='Time_Horizons')

    timeline_dict = {}
    for i, var in enumerate(time_horizon_df['Variable name']):
        timeline_string = time_horizon_df.loc[i, 'Time horizon']
        start_year = int(timeline_string[-4:]) # The last 4 characters in string are the start year
        timeline_dict[var] = list(range(start_year, 2100+1))

    # Dict to collect errors
    errors = {}

    # Dict to collect all data
    var_dict = {}

    # Which variables are converted?
    vars_to_convert = {}
    variables_df_dict = {}

    # Loop over all FTT models of interest
    for model in models.keys():
        scenarios = models[model][0]
        errors[model] = []
        var_dict[model] = {}

        # Get variable dimensions/attributes
        variables_df = pd.read_excel(os.path.join(dir_masterfiles, 'FTT_variables.xlsx'),
                                     sheet_name=model,
                                     true_values='y',
                                     false_values='n',
                                     na_values='-')
        variables_df_dict[model] = variables_df
        for i, var in enumerate(variables_df['Variable name']):
            var_dict[model][var] = {}
            var_dict[model][var]['Code'] = int(variables_df.loc[i, 'Code'])
            var_dict[model][var]['Desc'] = variables_df.loc[i, 'Description']
            var_dict[model][var]['Dims'] = [variables_df.loc[i, attr]
                                    for attr in ['RowDim', 'ColDim', '3DDim']
                                    if variables_df.loc[i, attr] not in [0, np.nan]]
            var_dict[model][var]['Read in?'] = variables_df.loc[i, 'Read in?']
            var_dict[model][var]["Conversion?"] = variables_df.loc[i, 'Conversion?']

            # Some variables are the same across scenarios, and should only
            # printed for the S0 scenario to save space
            var_dict[model][var]["Scenario"] = variables_df.loc[i, "Scenario"]
            var_dict[model][var]['Data'] = {}

    return variables_df_dict, var_dict, vars_to_convert, scenarios, timeline_dict

def get_model_classification(titles_path, variables_df):
    """Get the dimensions for the classifications"""
    dims = list(pd.concat([variables_df['RowDim'], variables_df['ColDim'], variables_df['3DDim']]))
    dims = list(set([dim for dim in dims if dim not in ['TIME', np.nan, 0]]))
    dims = {dim: None for dim in dims}

    titles_dict = load_titles()
    
    # Loop pulling out dimensions from the classifications data
    for dim in dims:
        if dim == 'RSHORTTI':
            dims[dim] = list(titles_dict['RTI_short'])
            
        else: 
            dims[dim] = list(titles_dict[dim])    

    return dims

#%%
# Main function

def convert_masterfiles_to_csv(models, ask_user_input=False, overwrite_existing_csvs=False):
    """
    The main function to convert masterfiles to csv files. 
    Depending on how you run it, it can have three types of behaviour:
        a) If you run it as a script, it will overwrite files. It will
        ask for confirmation before overwriting the gamma values
        b) If you call it from another function
            b1) It will generate csvs if files don't exist yet
            b2) It will overwrite files if the masterfiles are newer than the csv files
               This will include gamma values. 
    """
    
    # Define paths, directories and subfolders
    dir_inputs, dir_masterfiles, titles_path = directories_setup()
    variables_df_dict, var_dict, vars_to_convert, scenarios, timeline_dict = \
            variable_setup(dir_masterfiles, models)
            
    overwrite_existing_csvs_input = overwrite_existing_csvs
               
    for model in models.keys():
        overwrite_existing_csvs = overwrite_existing_csvs_input    # Reset to input value for each model
        
        variables_df = variables_df_dict[model]
        dims = get_model_classification(titles_path, variables_df)
        gamma_options = {"Ask user input": ask_user_input, 
                          "Overwrite user input": None}    
        
        ### ----------------------------------------------------------------------- ###
        ### ---------------------------- EXTRACT DATA ----------------------------- ###
        ### ----------------------------------------------------------------------- ###
       
        for scen in scenarios:
    
            # Define which sheets to convert
            vars_to_convert[model], sheets = \
                        get_sheets_to_convert(var_dict, model, scen)
            
            
            out_dir = os.path.join(dir_inputs, f'S{scen}', model)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            
            # Check if masterfiles are updated since last csv update (unless explicitly overwriting)
            if not overwrite_existing_csvs: 
                # Overwrite existing csv files when masterfile has more recently been updated
                overwrite_existing_csvs = are_csvs_older_than_masterfiles(
                        vars_to_convert, out_dir, models, model, scen, dir_masterfiles
                        )
            
            # Remove the variables for which csv files exist (except if they need overwriting)
            vars_to_convert[model], gamma_options = \
                    get_remaining_variables(vars_to_convert[model], out_dir, model, \
                                            var_dict, gamma_options, overwrite_existing_csvs)
            
            if len(vars_to_convert[model]) == 0:
                print("All variables already exist, no need to create CSV files")
                continue
            
            print("Initialising: extracting CSV input files. This can take a minute.")
            raw_data = read_data(models, model, dir_masterfiles, scen, sheets)
            if raw_data is None:
                continue
            
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
    
            # Read in sheet by sheet
            ci = 2              # Column indenting
            for i, var in enumerate(vars_to_convert[model]):
    
                ndims = len(var_dict[model][var]['Dims'])
                rdim, row_title = set_up_rows(model, var, var_dict, dims)
                cdim, col_title = set_up_cols(model, var, var_dict, dims, timeline_dict)
    
                excel_dim = len(ftt_titles[var_dict[model][var]['Dims'][0]])
                cf = ci + cdim                   # Final column
                sep = 1 + excel_dim - rdim
                sheet_name = var
    
                if ndims == 3:
                    
                    var_dict[model][var]['Data'][scen] = {}
                    
                    if var == "MGAM" and gamma_options["Overwrite user input"] == "skip":
                        continue
                    
                    for i, reg in enumerate(regs):          
                        ri = row_start + i*(rdim + sep)
                        data = extract_data(raw_data, sheet_name, ri, rdim, ci, cf)
    
                        var_dict[model][var]['Data'][scen][reg] = \
                            np.array(data.astype(np.float32))
    
                        write_to_csv(data, row_title, col_title, var, out_dir, reg)
                        
                        # Extract the gamma values from cost matrix
                        if var_dict[model][var]["Conversion?"] == "GAMMA":
                            if gamma_options["Overwrite user input"] == "skip":
                                continue
                            costs_to_gam(data, var, reg, timeline_dict, dims, out_dir)
                            
                elif ndims == 2:
                    
                    data = extract_data(raw_data, sheet_name, row_start, rdim, ci, cf)
                    var_dict[model][var]['Data'][scen] = np.array(data.astype(np.float32))
    
                    # Some variables have regions as second dimension in masterfile
                    # Transpose those
                    needs_transposing = variables_df.loc[variables_df["Variable name"] == var]["ColDim"] == "RSHORTTI"
                    if needs_transposing.item():
                        col_title, row_title = row_title, col_title
                        data = data.T
    
                    write_to_csv(data, row_title, col_title, var, out_dir)
    
                elif ndims == 1:
    
                    data = extract_data(raw_data, sheet_name, row_start, rdim, ci, cf)
    
                    # If a 1D variable needs to be converted into 2D
                    if var_dict[model][var]["Conversion?"] == "TIME":
                        convert_1D_var_to_timeline(data, var, row_title, out_dir, timeline_dict)
                        continue  # continue to the next variable
    
                    var_dict[model][var]['Data'][scen] = np.array(data.astype(np.float32))
                    write_to_csv(data, row_title, col_title, var, out_dir)
                    
                print(f"Data for {var} saved to CSV. Model: {model}")
    return var_dict

if __name__ == '__main__':
    """If you run this as a script, it will overwrite existing files"""
    # Structure of dict:
    # Model name: [Model name, [scenarios to read in], excel file]
    # Scenario 0 = Baseline
    # Scenario 1 = 2-degree scenario (default)
    # Scenario 2 = 1.5-degree scenario (default)

    models = {'FTT-Tr': [[0], 'FTT-Tr_31x71_2023'],
              'FTT-P': [[0], 'FTT-P-24x71_2022']}
            #  'FTT-H': [[0], 'FTT-H-13x70_2021'],
            #  'FTT-S': [[0], 'FTT-S-26x70_2021']}

    # models = {'FTT-IH-CHI': [[0], 'FTT-IH-CHI-13x70_2022'],
    #           'FTT-IH-FBT': [[0], 'FTT-IH-FBT-13x70_2022'],
    #           'FTT-IH-MTM': [[0], 'FTT-IH-MTM-13x70_2022'],
    #           'FTT-IH-NMM': [[0], 'FTT-IH-NMM-13x70_2022'],
    #           'FTT-IH-OIS': [[0], 'FTT-IH-OIS-13x70_2022'],
    # }

    var_dict = convert_masterfiles_to_csv(
        models, ask_user_input=True, overwrite_existing_csvs=True)
