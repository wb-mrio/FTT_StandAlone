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

#%%
# load csv


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
             


plot = ggplot(df_long[df_long['scenario'] == 'S3'], aes(x='year', y='value', color = 'technology')) + \
            geom_line() + \
                      facet_wrap('~ country') + \
        labs(title='Comparison of Variables by Technology and Country',
             x='Country',
             y='Generation',
             fill='Variable')