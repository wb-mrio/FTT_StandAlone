
# -*- coding: utf-8 -*-
"""
=========================================
output_functions.py
=========================================
Functions written for model outputs.

Functions included:
    - save_results
        Save model results to csvs

@author: ib400
"""

s0 = output_all['S0']
mcocx = s0['MCOCX']
mcoc = s0['MCOC']
mcocx_be = mcocx[0,:,0,:]
mcoc_be = mcoc[0,:,0,:]

mcocx_us = mcocx[37,:,0,:]
mcoc_us = mcoc[37,:,0,:]

mewg = s0['MEWG']
mewgx = s0['MEWGX']

mewg_us = mewg[37,:,0,:]
mewgx_us = mewgx[37,:,0,:]
repp = s0['REPP'][:,0,0,:]



# Standard library imports
import os
import copy

# Third party imports
import numpy as np


def save_results(name, years, results_list, results):
    """
    Save model results.

    Model results are saved in a series of structure csv files. The backend of
    the model frontend will read these csvs.

    Parameters
    ----------
    name: str
        Name of model run, and specification file read
    years: tuple (int, int)
        Bookend years of solution
    results_list: list of str
        List of variable names, specifying results to print
    results: dictionary of numpy arrays
        Dictionary containing all model results

    Returns
    ----------
    None:
        Detailed description

    Notes
    ---------
    This function is under construction.
    """

    # Create dictionary of variables to print, given results_list argument
    results_print = {k: results[k] for k in results_list}

    # Fetch metadata to print with NumPy arrays
    labels = load_labels(results_list)

    # Print csvs

    # Empty return
    return None
######################

import json
import pandas as pd
import pickle
import gzip

# Assuming output_dict is your model output dictionary
batch_number = 1  # Change this based on the current batch number

os.makedirs(os.path.dirname(f"{rootdir}\\Output\\"), exist_ok=True)     # Create Output folder if it doesn't exist
with open('Output\Results_S3.pickle', 'wb') as f:
    pickle.dump(output_all, f)
with gzip.open('Output\Results_S3.pickle.pkl.gz', 'wb') as f:
    pickle.dump(output_all, f)
    
# Save as JSON
with open('Output/S3_output.json', 'w') as json_file:
    json.dump(output_all, json_file)

# Convert to DataFrame and save as CSV (requires pandas)
df = pd.DataFrame.from_dict(output_dict, orient='index')
df.to_csv(f'output_batch_{batch_number}.csv')


## Large Save of all output
for scen in output_all.keys():
    print(scen. f' saved to Output/Results_{scen}.pickle')
    scenario = output_all[scen]
    
    with open(f'Output\Results_{scen}.pickle', 'wb') as f:
        pickle.dump(scenario, f)


## Designate core variables
variables_core = ['MWMC', 'MEWW', 'MEWS', 'MEWK', 'MEWI', 
                  'MEWG', 'MEWE', 'MEWD', 'METC', 'MRES', 
                  'MCOC', 'REPP', 'MWIY', 'MEWC', 'BCET', 
                  'MEWT', 'MEWR', 'MEFI']

# Loop through scenarios and rip out core vars
for scen in output_all.keys():
    
    scenario = output_all[scen]
    scen_core = {}
    for var in scenario.keys():
        if var in variables_core:
            scen_core[var] = scenario[var]
        else:
            pass
    
    with open(f'Output\Results_{scen}_core.pickle', 'wb') as f:
        pickle.dump(scen_core, f)

    print(scen, f' saved to Output/Results_{scen}_core.pickle')
    
    
    
    
    
    
    
    
    
    
    
    