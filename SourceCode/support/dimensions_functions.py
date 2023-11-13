"""
=========================================
dimensions_functions.py
=========================================
Functions to load dimensions names.

Functions included:
    - load_dim
        Load model dimensions
"""

# Standard library imports
import os

# Third party imports
import pandas as pd


def load_dims():
    """ Load model dimensions """

    # Declare file name
    dims_file = 'VariableListing.csv'

    # Check that classification titles file exists
    dims_path = os.path.join('utilities', 'titles', dims_file)
    if not os.path.isfile(dims_path):
        print('Dimensions name file not found.')

    dims_data = pd.read_csv(dims_path, skiprows=0, na_filter = False)
   
    # Iterate through csv rows and add to titles dictionary
    dims_dict = {}
    histend = {}
    forstart = {}
    domain = {}
    
    for index, row in dims_data.iterrows():
        dims_dict[row[0]] = row[3:7].tolist() if len(row) > 7 else []
        domain[row[0]] = row[7] if len(row) > 7 else None
        histend[row[0]] = int(row[9]) if row[9] not in ['-', ''] else ['']
        forstart[row[0]] = row[10] if len(row) > 10 else None
    
    # Return titles dictionary
    return dims_dict, histend, domain, forstart
