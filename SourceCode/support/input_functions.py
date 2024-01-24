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

#@njit(nopython=False)
#def load_data(titles, dimensions, start, end, scenarios):
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
    titles = titles
    titles['TIME'] = timeline

    # Load dimensions
    dims = dimensions

    #Declare list of scenarios
    scenario_list = [x.strip() for x in scenarios.split(',')]
    scenario_list = ["S0"] + [x for x in scenario_list if x != "S0"]

    modules_enabled = [x.strip() for x in ftt_modules.split(',')]
    modules_enabled += ['General']

    #Create container with the correct dimensions
    data = {scen : { var : np.zeros([len(titles[dims[var][0]]), len(titles[dims[var][1]]),
                                     len(titles[dims[var][2]]), len(titles[dims[var][3]])]) for var in dims}
                    for scen in scenario_list}


    for scen in data:

        if scen != 'S0':

            data[scen] = copy.deepcopy(data['S0'])

        for ftt in modules_enabled:

#            if "General" == ftt: print("oi")

            # Start reading CSVs
            directory = os.path.join('Inputs', scen, ftt)

            for root, dirs, files in os.walk(directory):

                # Loop through all the files in the directory
                for file in files:

                    if file.endswith(".csv"):

                        # Read the csv
                        csv = pd.read_csv(os.path.join(root, file), header=0,
                                          index_col=0).fillna(0)

                        # Split file name
                        file_split = file[:-4].split('_')

                        var = file_split[0]

#                        if var == 'MEWDX':
#                            print('stop')

                        if len(file_split) == 1:

                            key = None

                        else:

                            key = file_split[1]

                        # User warning for variables that are present in the folder but not used
                        if var not in data[scen].keys():

                            warnings.warn('Variable {} is present in the folder as a csv but is not included \
                                          in VariableListing, so it will be ignored'.format(var))


                        else:

#                            if var == "MEFI":
#                                print(var)

                            if dims[var][3] == 'TIME':

                                var_tl = list(range(int(forstart[var]), timeline[-1]+1))
                                var_tl_fit = [year for year in var_tl if year in timeline]
                                var_tl_inds = [i for i, year in enumerate(timeline) if year in var_tl]
                                # print(csv.columns, var)
                                try:
                                    csv.columns = [int(year) for year in csv.columns]
                                except ValueError as e:
                                    print(f"'{var}'")
                                    raise e


                                #print(file)
                                read = csv.loc[:, var_tl]


                            else:

                                read = csv

                            # If the CSV file has a region key indicator then it's 3D
                            if key in titles['RTI_short']:

                                # Take the index of the region
                                reg_index = titles['RTI_short'].index(key)

                                # Loop through the second dimension
                                for i in range(read.shape[0]):

                                    if var == "MCSC":
                                        x = 1 +1

                                    # Distinction whether the last dimension is time or not
                                
                                    if len(titles[dims[var][3]]) == 1:
                                            data[scen][var][reg_index, i, :, 0] = read.iloc[i, :]
                        
                                    else:            
                                            # data[scen][var][reg_index, i, 0, var_tl_inds[0]:var_tl_inds[-1]+1] = read.iloc[i, :len(var_tl_fit)]
                                            # print(var, key)
                                            data[scen][var][reg_index, i, 0, var_tl_inds[0]:var_tl_inds[-1]+1] = read.iloc[i][var_tl_fit]                       
                                        
                           # If the variable does not have a key
                            else:
                                
                                # Distinction between various cases
                                if dims[var][0] == 'RTI':
                                
                                    # RHUD specific case
                                    if len(titles[dims[var][3]]) > 1 and len(titles[dims[var][1]]) == 1 and len(titles[dims[var][2]]) == 1:
                                        data[scen][var][:, 0, 0, var_tl_inds[0]:var_tl_inds[-1]+1] = read.iloc[:][var_tl_fit]
                                    
                                    # HJFC specific case (the csv has been transposed need to check if this is correct)
                                    elif len(titles[dims[var][1]]) > 1 and len(titles[dims[var][2]]) == 1 and len(titles[dims[var][3]]) == 1:
                                        try:
                                            data[scen][var][:, :, 0, 0] = read.T
                                        except ValueError as ve:
                                            print(f"'{var}'")
                                            raise ve
                                            print(read.shape)
                                    
                                    # For all variables that are not country specific (no RTI)
                                    else:
                                        if dims[var][0] == 1:
                                                
                                            # if there is no time variable
                                            if len(titles[dims[var][1]]) > 1 and len(titles[dims[var][2]]) > 1:
                                                    data[scen][var][0, :, :, 0] = read.iloc[:, :len(titles[dims[var][2]])]
                                            
                                            # if there is a time variable
                                            elif len(titles[dims[var][3]]) > 1 and len(titles[dims[var][1]]) > 1:
                                                data[scen][var][0, :, 0, var_tl_inds[0]:var_tl_inds[-1]+1] = read.iloc[:][var_tl_fit]
                                             
                                                
                                            else:
                                                if all([len(titles[dims[var][x]]) == 1 for x in range(4)]):
                                                    data[scen][var][0, 0, 0, 0] = read.iloc[0,0]           

#            #For the scenarios, copy from the baseline the variables that are not in the scenario folder
#            if scen != 'S0':
#
#                for var in data[scen]:
#
#                    if len(dims[var]) > 2 and dims[var][0] == 'RTI':
#
#                        for r, reg in enumerate(titles['RTI']):
#
#                            if np.all(data[scen][var][r, :, :, :]==0):
#
#                                 data[scen][var][r, :, :, :]= data['S0'][var][r, :, :, :].copy()
#
#                    elif np.all(data[scen][var]==0):
#
#                        data[scen][var] = data['S0'][var].copy()



    data_return = copy.deepcopy(data)

    # Return data
    return data_return


def results_instructions():
    """ Read result instruction file. """

    # Load instructions file
    results_list = {}

    # Return data
    return results_list

