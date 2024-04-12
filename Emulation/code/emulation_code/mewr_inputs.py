# -*- coding: utf-8 -*-
"""
Created on Fri Dec  1 12:56:58 2023

Code for generating new MEWR input sheets for all countries, except PK as 
produced from old masterfile

Future developments: implement new masterfile (2022) with new MEWR configuration

@author: ib400
"""

import os
import pandas as pd

os.chdir("C:/Users/ib400/OneDrive - University of Exeter/Documents/GitHub/FTT_StandAlone")

#%% 

master_path = "Inputs/_MasterFiles/FTT-P/FTT-P-24x70_2021_S0.xlsx"
sheet_name = 'MEWR'

master = pd.read_excel(master_path, sheet_name = sheet_name, 
                       usecols=lambda col: col not in [0], skiprows=4, header=None) # get this into input_wrangle.py
                    
for i in range(0, 70*36, 36):
    
    df = master.iloc[i: i + 25, :]
    country = df.iloc[0,0]
    df.iloc[0,0] = ''
    
    file_name = f'{sheet_name}_{country}'
    df.to_csv(f'Inputs/S0/FTT-P/{file_name}.csv', header = False, index = False)
    print(file_name + ' saved to Inputs/S0/FTT-P')

        
      
        
      
        
      
        
      
        
      
        
      
        
    