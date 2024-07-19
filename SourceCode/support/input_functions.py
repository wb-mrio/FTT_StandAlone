# -*- coding: utf-8 -*-
"""
=========================================
input_functions.py
=========================================
Collection of functions written for model inputs.

Functions included:
    - load_data
        Load all model data for all variables and all years.
    - results_instructions
        Read results instruction file.

"""

# Standard library imports
import os
import copy
import warnings

# Third party imports
import numpy as np
import pandas as pd
from numba import njit

from SourceCode.support.debug_messages import input_functions_message

#@njit(nopython=False)
def load_data(titles, dimensions, timeline, scenarios, ftt_modules, forstart):
    """
    Load all model data for all variables and all years.

    Parameters
    ----------
    titles: dictionary of lists
        Dictionary containing all title classifications
    dimensions: dict of tuples (str, str, str, str)
        Variable classifications by dimension
    timeline: list of int
        Years of both historical data and forecast period
    scenarios:

    Returns
    ----------
    data_return: dictionary of numpy arrays
        Dictionary containing all required model input variables.
    """

    # Read titles and assign time dimension
    titles['TIME'] = timeline

    # Load dimensions
    dims = dimensions

    # Declare list of scenarios
    scenario_list = [x.strip() for x in scenarios.split(',')]
    scenario_list = ["S0"] + [x for x in scenario_list if x != "S0"]

    modules_enabled = [x.strip() for x in ftt_modules.split(',')]
    modules_enabled += ['General']

    # Create container with the correct dimensions
    data = {
        scen : {
            var : np.zeros([
                len(titles[dims[var][0]]),
                len(titles[dims[var][1]]),
                len(titles[dims[var][2]]),
                len(titles[dims[var][3]])
            ]) for var in dims
        } for scen in scenario_list
    }


    for scen in data:
        if scen != 'S0':
            data[scen] = copy.deepcopy(data['S0'])


        for ftt in modules_enabled:

            # Start reading csv files
            directory = os.path.join('Inputs', scen, ftt)

            # Check if the directory exists (skipping General for some scenarios)
            if not os.path.isdir(directory):
                csv_files = []
            else:
                # Get a list of all CSV files in the directory
                csv_files = [f for f in os.listdir(directory) if f.endswith(".csv")]

            # Get a set of variables in generated from VariableListing
            valid_vars = set(var.split('_')[0] for var in data[scen].keys())

            # Warn for variables that are present in the folder but not used
            for file in csv_files:
                var = file[:-4].split('_')[0]
                if var not in valid_vars:
                    warnings.warn(f'Variable {var} is present in the folder as a csv but is not included \
                                in VariableListing, so it will be ignored')
            
            # Filter the list to include only the files that correspond to variables in data[scen].keys()
            csv_files = [f for f in csv_files if f[:-4].split('_')[0] in valid_vars]
            
            
            # Loop through all the files in the directory
            for file in csv_files:

                # Construct the full file path
                file_path = os.path.join(directory, file)

                # Read the csv
                csv = pd.read_csv(file_path, header=0, index_col=0).fillna(0)

                # Split file name
                file_split = file[:-4].split('_')
                var = file_split[0]

                if len(file_split) == 1:
                    key = None
                else:
                    key = file_split[1]
                
                # The length of the dimensions
                dims_length = [len(titles[dims[var][x]]) for x in range(4)]

                
                # If the fourth dimension is time
                if dims[var][3] == 'TIME':
                    var_tl = list(range(int(forstart[var]), timeline[-1]+1))
                    var_tl_fit = [year for year in var_tl if year in timeline]
                    var_tl_inds = [i for i, year in enumerate(timeline) if year in var_tl]
                    csv.columns = [int(year) for year in csv.columns]

                    read = csv.loc[:, var_tl]

                else:
                    read = csv

                # If the csv file has a region key indicator (like _BE)
                if key in titles['RTI_short']:

                    # Take the index of the region
                    reg_index = titles['RTI_short'].index(key)

                    # Loop through the second dimension
                    for i in range(read.shape[0]):

                        # Distinction whether the last dimension is time or not
                        if dims_length[3] > 1:
                            try:
                                data[scen][var][reg_index, i, 0, var_tl_inds[0]:var_tl_inds[-1]+1] = read.iloc[i][var_tl_fit]
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read, var_tl_fit, reg_index)
                                raise(e)
                        else:
                            try:
                                data[scen][var][reg_index, i, :, 0] = read.iloc[i, :]
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read, reg_index = reg_index)
                                raise(e)
                            

                # If the file does not have a region key like _BE
                else:

                    # If the first dimension is regions
                    # Quick fix for ZLER (first dim here is FTTI)
                    if (dims[var][0] == 'RTI') or (var == "ZLER"):
                        # If there are only regions
                        if all(dim_length == 1 for dim_length in dims_length[1:]):
                            try:
                                data[scen][var][:, 0, 0, 0] = read.iloc[:, 0]
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read)
                                raise(e)
      
                        # If there is a second dimension # TODO: check if this is correct
                        if dims_length[1] > 1:
                            try: 
                                data[scen][var][:, :, 0, 0] = read
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read, reg_index = reg_index)
                                raise(e)
                        
                        # If there is a third dimension only
                        elif dims_length[2] > 1:
                        #elif len(titles[dims[var][2]]) > 1:
                            print("Test if this is ever used")
                            try:
                                data[scen][var][:, 0, :, 0] = read
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read)
                                raise(e)    
                        
                        # If there is a fourth dimension only (time)
                        elif dims_length[3] > 1:
                            try:
                                data[scen][var][:, 0, 0, var_tl_inds[0]:var_tl_inds[-1]+1] = read.iloc[:][var_tl_fit]
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read, timeline=var_tl_fit)
                                raise(e)

                    # If the first dimension is not regions
                    else:
                        # If there is only one number
                        if all(dim_length == 1 for dim_length in dims_length):
                            try: 
                                data[scen][var][0, 0, 0, 0] = read.iloc[0,0]
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read)
                                raise(e)

                        # If there is no third dimension
                        # Quick fix for sectorcoupling variable which has no 3rd dim but also no time
                        elif dims_length[2] == 1 and var != 'SectorCouplingAssumps':
                            try:
                                data[scen][var][0, :, 0, var_tl_inds[0]:var_tl_inds[-1]+1] = read.iloc[:][var_tl_fit]
                            except (IndexError, ValueError, KeyError) as e:
                                input_functions_message(scen, var, dims, read, timeline=var_tl_fit)
                                raise(e)

                        # If there is no time dimension (fourth dimension)
                        elif dims_length[3] == 1:
                            try:
                                data[scen][var][0, :, :, 0] = read.iloc[:,:len(titles[dims[var][2]])]
                            except (IndexError, ValueError) as e:
                                input_functions_message(scen, var, dims, read)
                                raise(e)
    return data


def results_instructions():
    """ Read result instruction file. """

    # Load instructions file
    results_list = {}

    # Return data
    return results_list
