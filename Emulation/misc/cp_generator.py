# -*- coding: utf-8 -*-
"""
Created on Mon Oct  2 10:22:14 2023

Carbon Tax Generation Script from E3ME data, only needed for generating S{}_REPP.csv
which is then used for rest of the work flow


@author: ib400
"""

import os
import pandas as pd
from openpyxl import load_workbook
from tqdm import tqdm
import random
import numpy as np
from scipy.stats import poisson, binom, uniform, norm, randint
os.chdir('C:/Users/ib400/OneDrive - University of Exeter/Documents/GitHub/FTT_StandAlone')

#%% take input and split 

for i in list(os.listdir('Emulation/data/cp_data')):
    input_name = os.path.splitext(i)[0]
    # read in input file
    df = pd.read_csv(f'Emulation/data/cp_data/{input_name}.csv', skiprows=1)
    # split name col drop orig
    df[['scen', 'country']] = df['time'].str.split(';', expand = True)
    df = df.drop(columns = ['time'])
    ## Move the last column to the front
    df = df[['scen', 'country'] + [col for col in df.columns if col != 'scen' and col != 'country']]
    # convert country col
    df['country'] = df['country'].str.extract(r'\((\w+)\)')
    # change scen names -- GENERALISE **********
    df.loc[df['scen'] == 'Dan_ba', 'scen'] = 'S0'
    df.loc[df['scen'] == 'Dan_IN_NetZero13', 'scen'] = 'S3'
    # Save baseline inputs ####' Generalise
    s0 = df[df['scen'] == 'S0']
    s0.drop(columns = ['scen'], inplace = True)
    s0 = s0.rename(columns = {'country': ''})
    s0.to_csv(f'Inputs/S0/FTT-P/{input_name}.csv', index = False)
    # Save ambitious inputs
    s3 = df[df['scen'] == 'S3']
    s3.drop(columns = ['scen'], inplace = True)
    s3 = s3.rename(columns = {'country': ''})
    s3.to_csv(f'Emulation/data/cp_ambit/S3_{input_name}.csv', index = False)
    #saved to general folder for ambition variation
    print(input_name + ' saved')



#%%

    

