
# -*- coding: utf-8 -*-
"""
This script makes preperation to extract data from FTT masterfiles in the
"/In/FTTAssumptions/[model]" folders and save them in separate csv files.

@author: Femke
"""

import os
import glob

from pathlib import Path
import os



# Local library imports
from SourceCode.support.convert_masterfiles_to_csv import convert_masterfiles_to_csv


def initialise_csv_files(ftt_modules, scenarios):
    """
    This function initialises the csv files for the model run.
    It takes the enabled modules and scenarios from the settings.ini file
    as input and converts the masterfiles to csv files.

    Args:
    ftt_modules (list): List of enabled modules
    scenarios (list): List of scenarios

    Returns:
    None
    """
    # Get the masterfiles
    ftt_modules = ftt_modules.split(', ')
    scenarios = scenarios.split(', ')

    model_list = generate_model_list(ftt_modules, scenarios)

    # Convert masterfiles to csv
    convert_masterfiles_to_csv(model_list)


def get_masterfile(ftt_module, scenario):
    """Find the matching file name

    Returns:
    The filename that matches
    The middle bit of the file names for input to convert_masterfiles_to_cvs
    """
    
    # The * denotes the regionxtechnologies and last year updated part of the string
    file_pattern = f"{ftt_module}*_{scenario}.xlsx"
    matching_file = list(
        (Path('Inputs') / '_MasterFiles' / ftt_module).glob(file_pattern)
    )

    # Printing warnings 1: in case there is no corresponding excel file
    if len(matching_file) == 0:
        print(f"Warning: No files matched the pattern for module {ftt_module} and scenario {scenario}.")
        print(f"This means {ftt_module}: {scenario} will rely only on pre-specified csv files.")
        matching_file = None
        file_root = None
        return matching_file, file_root
    
    # Printing warnings 2: in case multiple files are found
    elif len(matching_file) > 1:
        print(f"Warning: Multiple files matched the pattern for module {ftt_module} and scenario {scenario}.")

    # Select part of the filename without the scenario or xlsx extension
    try:
        base_name = os.path.basename(matching_file[0]) # file name without directory
        end_index = base_name.index(f'_{scenario}.xlsx')
        file_root = base_name[:end_index]
    except IndexError as e:
        print("An error occurred while finding the masterfile.")
        print(f"the ftt model and scenario: {ftt_module}, {scenario}")
        print(f"The file that triggered the error: {matching_file}")
        raise e


    return matching_file, file_root


def generate_model_list(ftt_modules, scenarios):
    """
    Using the models and scenarios from the settings.ini file,
    put these into a dictionary.

    Remove the pseudo-scenario gamma, as this should not be initialised separately
    """
    # Remove Gamma pseudo-scenario for initialisation
    scenarios = [item for item in scenarios if item != "Gamma"]

    models = {}

    for module in ftt_modules:
        module_scenarios = []
        for scenario in scenarios:
            matching_file, file_root = get_masterfile(module, scenario)
            if matching_file:
                # TODO: rewrite this and other code to allow for other types of scenario names
                module_scenarios.append(int(scenario[1:]))
        if module_scenarios:
            models[module] = [module_scenarios, file_root]
    return models

