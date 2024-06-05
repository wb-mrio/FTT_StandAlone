
# -*- coding: utf-8 -*-
"""

Script for changing all values of a mastersheet to certain values, only first vars where
time is one of the dimensions

@author: ib400
"""
#%% Importing libraries
import pandas as pd
import numpy as np
from openpyxl import load_workbook
import os

# %%

def convert_all(master_path, model_dir, value, sheet_name="MGAM"):
    master_path = master_path
    model_dir = model_dir
    value = value
    sheet_name = sheet_name
    
    # Number of regions, set to 71 for all
    n_regions = 71
    snipppet_length = 35
    iter_length = snipppet_length + 1

    columns = np.arange(2001, 2101)
    index = np.arange(1, snipppet_length + 1)
    changes_df = pd.DataFrame(columns=columns, index=index)
    changes_df = changes_df.fillna(value)

    # Editing all gamma values to 0
    with pd.ExcelWriter(os.path.join(model_dir, master_path), mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:

        for i in np.arange(0, n_regions + 1):
            # startcol is just the place in the sheet the data starts and the +5 is to skip the header
            changes_df.to_excel(writer, sheet_name= sheet_name,
                                                startcol=2, startrow = i*iter_length+5, header=False, index=False)
# %%
convert_all(model_dir = "Inputs/_Masterfiles/FTT-P", master_path = "FTT-P-24x71_2022_S0.xlsx", sheet_name = "MGAM", value = 0)
# %%
check = pd.read_excel("Inputs\_Masterfiles\FTT-P\FTT-P-24x71_2022_S0.xlsx", sheet_name="MGAM")
# %%
