
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

#%% Defining paths and model variables

model_to_change = "FTT-P"
master_path = "FTT-P-24x71_2022_S0.xlsx"
dir_excel = os.path.join(f"Inputs\_Masterfiles\{model_to_change}", master_path)
sheet_name = "MGAM"

# Number of regions, set to 71 for all
n_regions = 71


columns = np.arange(2000, 2101)
index = np.arange(1, n_regions + 1)
changes_df = pd.DataFrame(columns=columns, index=index)
changes_df = changes_df.fillna(-1)


#%%
# Editing all gamma values to 0
with pd.ExcelWriter(dir_excel, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:

    for i in np.arange(0, n_regions):
        onshore_generation.iloc[[i]].to_excel(writer, sheet_name= sheet_name,
                                            startcol=12, startrow=onshore_ind+i*36, header=False, index=False)
        offshore_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                            startcol=12, startrow=offshore_ind+i*36, header=False, index=False)
        solar_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                            startcol=12, startrow=solar_ind+i*36, header=False, index=False)
        csp_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                        startcol=12, startrow=thermal_ind+i*36, header=False, index=False)
        lhydro_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                            startcol=12, startrow=lhydro_ind+i*36, header=False, index=False)
        phs_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                        startcol=12, startrow=phs_ind+i*36, header=False, index=False)
        tidal_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                            startcol=12, startrow=tidal_ind+i*36, header=False, index=False)
        sbiomass_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                            startcol=12, startrow=sbiomass_ind+i*36, header=False, index=False)
        biogas_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                            startcol=12, startrow=biogas_ind+i*36, header=False, index=False)
        geoth_generation.iloc[[i]].to_excel(writer, sheet_name="MEWG",
                                            startcol=12, startrow=geoth_ind+i*36, header=False, index=False)

        onshore_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=onshore_ind+i*36, header=False, index=False)
        offshore_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=offshore_ind+i*36, header=False, index=False)
        solar_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=solar_ind+i*36, header=False, index=False)
        csp_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                startcol=6, startrow=thermal_ind+i*36, header=False, index=False)
        lhydro_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=lhydro_ind+i*36, header=False, index=False)
        phs_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                startcol=6, startrow=phs_ind+i*36, header=False, index=False)
        tidal_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=tidal_ind+i*36, header=False, index=False)
        sbiomass_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=sbiomass_ind+i*36, header=False, index=False)
        biogas_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=biogas_ind+i*36, header=False, index=False)
        geoth_capacity_exogenous.iloc[[i]].to_excel(writer, sheet_name="MWKA",
                                                    startcol=6, startrow=geoth_ind+i*36, header=False, index=False)
        
        onshore_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=onshore_ind+i*36, header=False, index=False,)
        offshore_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=offshore_ind+i*36, header=False, index=False)
        solar_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=solar_ind+i*36, header=False, index=False)
        csp_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                startcol=6, startrow=thermal_ind+i*36, header=False, index=False)
        lhydro_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=lhydro_ind+i*36, header=False, index=False)
        phs_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                startcol=6, startrow=phs_ind+i*36, header=False, index=False)
        tidal_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=tidal_ind+i*36, header=False, index=False)
        sbiomass_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=sbiomass_ind+i*36, header=False, index=False)
        biogas_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=biogas_ind+i*36, header=False, index=False)
        geoth_cf.iloc[[i]].to_excel(writer, sheet_name="MWLO",
                                    startcol=6, startrow=geoth_ind+i*36, header=False, index=False)






# %%
