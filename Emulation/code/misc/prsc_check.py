# -*- coding: utf-8 -*-
"""
Created on Mon Nov 13 10:41:49 2023

Checking the differences between inputs for base and ambitious scenarios scens

@author: ib400
"""
import pandas as pd
import numpy as np

prsc = pd.read_csv('Emulation/data/PRSC.csv')
prsc_amb = pd.read_csv('Emulation/data/cp_ambit/S3_PRSC.csv')

p_2050 = prsc['2050']
p_amb_2050 = prsc_amb['2050']

compare_base_amb = p_2050/p_amb_2050*100

prscx = output_all['S0']['PRSCX'][:,0,0,:]
prscx_2050 = prscx[:,40]

compare_base_e3me = p_2050/prscx_2050*100
compare_amb_e3me = p_amb_2050/prscx_2050*100


## EU ambition variation

# Define the number of runs
num_runs = 200

# Generate values for the first parameter
param1_values = np.linspace(0, 1, num_runs)

# Initialize an empty list to store combinations
combinations = []

# Iterate over the values of the first parameter
for val1 in param1_values:
    # Calculate the corresponding value for the second parameter
    val2 = 1 - val1
    
    # Append the combination to the list
    combinations.append((val1, val2))

# Print the resulting combinations
for i, (val1, val2) in enumerate(combinations, 1):
    print(f"Run {i}: Parameter 1 = {val1}, Parameter 2 = {val2}")



# Define the number of runs
num_runs = 200

# Generate values for both parameters
param1_values = np.linspace(0, 1, int(np.sqrt(num_runs)))
param2_values = np.linspace(0, 1, int(np.sqrt(num_runs)))

# Initialize an empty list to store combinations
combinations = []

# Iterate over the values of both parameters
for val1 in param1_values:
    for val2 in param2_values:
        combinations.append((val1, val2))

# Print the resulting combinations
for i, (val1, val2) in enumerate(combinations, 1):
    print(f"Run {i}: Parameter 1 = {val1}, Parameter 2 = {val2}")
