# -*- coding: utf-8 -*-
"""
Created on Mon Apr 15 16:05:48 2024

Script for plotting output of scenarios for comparison

@author: ib400
"""

import os 
import pandas as pd
import numpy as np
from plotnine import ggplot, aes, geom_bar, facet_wrap, labs, geom_line
os.chdir(r'C:\Users\ib400\OneDrive - University of Exeter\Desktop\PhD\GitHub\FTT_StandAlone')

#%%
# load csv
df = pd.read_csv('Output\S0_S3_long.csv')

#%%
# Plotting with plotnine
# designate variables and countries of interest
countries = ['US', 'CN', 'DE', 'IN']
variables = ['MEWS']
techs = ['1 Nuclear', '2 Oil', '7 CCGT', '3 Coal', \
         '17 Onshore', '18 Offshore', 
         '19 Solar PV']

df_long = df[df['country_short'].isin(countries) \
             & df['variable'].isin(variables) \
             & df['technology'].isin(techs)]
             


ggplot(df_long[df_long['scenario'] == 'S0'], aes(x='year', y='value', color = 'technology')) + \
            geom_line() + \
                      facet_wrap('~ country') + \
        labs(title='Comparison of Variables by Technology and Country',
             x='Country',
             y='Generation',
             fill='Variable')