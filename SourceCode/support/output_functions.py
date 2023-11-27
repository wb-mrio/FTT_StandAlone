# -*- coding: utf-8 -*-
"""
=========================================
output_functions.py
=========================================
Functions written for model outputs.

Functions included:
    - save_results
        Save model results to csvs
"""

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
