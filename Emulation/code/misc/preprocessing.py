# -*- coding: utf-8 -*-
"""
Created on Thu Jan  6 13:57:54 2022

@author: Femke
"""

import os
from celib import MRE     # MRE is the special data structure for output of E3ME files
import pandas as pd       # pandas is a library for structured data (not simply a matrix, but a matrix with named columns and rows)
import matplotlib.pyplot as plt # plt is the standard plotting library
import numpy as np        # scientific computing library
import seaborn as sns     # fancy plotting library
import matplotlib.pylab as pylab
from pathlib import Path
import csv


# %% Read in MRE data
def get_df(scenarios, scenarios_to_print, start_year, dirp_out, regs_to_print, print_temperature=True):
    y1 = start_year - 2010 # Years after 2010
    y2 = 0 # Years before end (uncomment next line if you change this)
    y3 = 2061 # End year + 1
    #y1: = np.arange(y1, 51-y2)
    
    var_dic = {'solar': 18, 'hydro': 15, 'wind': 16, 'offshore wind': 17}
    #%% 
    # Functions
    def data_per_region(raw_mewg, scen, inds):
        '''Compute generation shares renewables and solar'''  
        
        mewg = np.sum(np.array(raw_mewg[scen])[inds], axis=0)
        mewg_ren_share = np.sum(mewg[8:22], axis=0)/np.sum(mewg, axis=0)*100
        mewg_solar_share = np.sum(mewg[18:20], axis=0)/np.sum(mewg, axis=0)*100
        
        return list(mewg_ren_share), list(mewg_solar_share)
    
    
    def mewk_share(raw_mewk, scen, inds):
        '''Compute capacity share variable renewables''' 
        
        mewk_global = np.sum(np.array(raw_mewk[scen]), axis=0)               # Should give 2D array with technology and time axes
        mewk_inds = np.sum(np.array(raw_mewk[scen])[inds], axis=0)           # Should give you same dimension 
        
        # Ignore errors, as the first two years are zeros
        with np.errstate(divide='ignore', invalid='ignore'):
            mewk_solar_share = mewk_inds[18] / mewk_global[18] *100
            mewk_onshore_share = mewk_inds[16] / mewk_global[16] * 100
            mewk_offshore_share = mewk_inds[17] / mewk_global[17] * 100
        
        return list(mewk_solar_share)[y1:] + list(mewk_onshore_share)[y1:] + list(mewk_offshore_share)[y1:]
    
    
    def tech_per_region(raw_mewg, scen, inds, technology):
        ''' Compute shares of technologies by region '''
        tech_list = ["Nuclear", "Oil", "Coal", "Coal + CCS", "IGCC", "IGCC + CCS", 
                    "CCGT", "CCGT + CCS", "Solid Biomass", "S Biomass CCS", 
                    "BIGCC", "BIGCC + CCS", "Biogas", "Biogas + CCS", "Tidal",
                    "Hydro", "Onshore wind", "Offshore wind", "Solar PV", "CSP",
                    "Geothermal", "Wave", "Fuel Cells", "CHP"]
        technology_name = tech_list[technology]
        mewg = np.sum(np.array(raw_mewg[scen])[inds], axis=0)
        mewg_tech_share = mewg[technology]/np.sum(mewg, axis=0)*100
        if technology == 1: # Switch coal and oil
            mewg_tech_share = np.sum(mewg[2:4], axis=0)/np.sum(mewg, axis=0)*100
            technology_name = "Coal"
        if technology == 2: # Oil
            mewg_tech_share = mewg[1]/np.sum(mewg, axis=0)*100
            technology_name = "Oil"
        if technology == 4: # Sum gas
            mewg_tech_share = np.sum(mewg[4:8], axis=0)/np.sum(mewg, axis=0)*100
            technology_name = "Gas"

        #if technology == 5: # Sum gas + CCS
        #    mewg_tech_share = np.sum(mewg[5:8:2], axis=0)/np.sum(mewg, axis=0)*100
        #    technology_name = "Gas + CCS"
        if technology == 8: # Sum bioenergy
            mewg_tech_share = np.sum(mewg[8:14], axis=0)/np.sum(mewg, axis=0)*100
            technology_name = "Bioenergy"
        # if technology == 9:
        #     mewg_tech_share = np.sum(mewg[9:14:2], axis=0)/np.sum(mewg, axis=0)*100
        #     technology_name = "Bioenergy + CCS"
        if technology == 14:
            inds_other = [14, 20, 21, 22, 23]
            mewg_tech_share = np.sum(mewg[inds_other], axis=0)/np.sum(mewg, axis=0)*100
            technology_name = "Other"
        if technology in [3, 5, 6, 7, 9, 10, 12, 11, 13, 20, 21, 22, 23]:
            return None, "Elsewhere aggregated"
          
        return list(mewg_tech_share), technology_name
    
    # def veh_per_region(raw_tewk, scen, inds):
    #     ''' Compute shares renewables and solar   '''     
    #     tewk = np.sum(np.array(raw_tewk[scen])[inds], axis=0)
    #     tewk_elec_share = np.sum(tewk[18:21], axis=0)/np.sum(tewk, axis=0)*100
    #     #mewg_solar_share = np.sum(mewg[18:20], axis=0)/np.sum(mewg, axis=0)*100
        
    #     return list(tewk_elec_share)
    
    def average_region(raw_var, raw_mewg, scen, inds, source):
        ''' Weight by generation of the power source (both to compare technologies + to compare countries)'''
        
        
        if source in ['solar', 'hydro', 'wind', 'offshore wind']:
            var = np.array(raw_var[scen])[inds, var_dic[source]]
            mewg = np.array(raw_mewg[scen])[inds, var_dic[source]]  # Shape
            if len(inds) > 1:
                try:
                    var = np.average(var, weights=mewg, axis=(0))
                except ZeroDivisionError:
                    shape = var[0].shape[0]
                    var = np.full([shape], np.nan)
            else:
                var = var[0]
                
        elif source =='coal':
            var = np.array(raw_var[scen])[inds, 2]
            mewg = np.array(raw_mewg[scen])[inds, 2]  # Shape
            if len(inds) > 1:
                try:
                    var = np.average(var, weights=mewg, axis=(0))
                except ZeroDivisionError:
                    shape = var[0].shape[0]
                    var = np.full([shape], np.nan)
            else:
                var = var[0]
        elif source =='nuclear':
            var = np.array(raw_var[scen])[inds, 0]
            mewg = np.array(raw_mewg[scen])[inds, 0]  # Shape
            if len(inds) > 1:
                try:
                    var = np.average(var, weights=mewg, axis=(0))
                except ZeroDivisionError:
                    shape = var[0].shape[0]
                    var = np.full([shape], np.nan)
            else:
                var = var[0]
        elif source == 'gas':
            var = np.array(raw_var[scen])[inds]
            var = var[:, [6]]
            mewg = np.array(raw_mewg[scen])[inds]  # Shape
            mewg = mewg[:, [6]]
            try:
                var = np.average(var, weights=mewg, axis=(0, 1))
            except ZeroDivisionError:
                shape = var[0, 0].shape[0]
                var = np.full([shape], np.nan)

        return list(var)

    #%%
    # Define empty dictionaries for data output
    raw_FCO2 = {}        
    raw_mewg = {}
    raw_mewk = {}
    raw_cghg = {}
    raw_RCO2 = {}
    raw_mewc = {}
    raw_metc = {}
    raw_rgdp = {}
    raw_fret = {}
    raw_kre = {}
    raw_mssp = {}
    raw_mlsp = {}
    raw_mlsm, raw_mssm = {}, {}
    raw_mewl = {}
    raw_tfec = {}
    raw_mewe = {}
    
    raw_mklb = {}
    raw_mwg1 = {}
    raw_mwg2 = {}
    raw_mwg3 = {}
    raw_mwg4 = {}
    raw_mwg5 = {}
    raw_mwg6 = {}

    
    mewg_ren_share, mewg_solar_share, country, scenario_df, year, E3ME_region = [], [], [], [], [], []
    mewe, mewg_onshore, mewg_offshore = [], [], []
    lcoe_solar, lcoe_coal, lcoe_gas, lcoe_bare_solar, lcoe_bare_coal, lcoe_bare_nuclear, \
    lcoe_bare_gas, lcoe_bare_hydro, lcoe_bare_wind, lcoe_bare_offshore = [], [], [], [], [], [], [], [], [], []
    FCO2_ba, FCO2_2010, FCO2 = [], [], []
    fret, tfec, kre_frac, kre, kre_2019_benchmark = [], [], [], [], []
    mwg1, mwg2, mwg3, mwg4, mwg5, mwg6 = [], [], [], [], [], []
    mwg_gas1, mwg_gas2, mwg_gas3, mwg_gas4, mwg_gas5, mwg_gas6 = [], [], [], [], [], []

    
    for scen, mre_f in scenarios.items():
        if scen in scenarios_to_print:
            mre_path = os.path.join(dirp_out, mre_f)
            with MRE(mre_path) as mre:
                raw_mewg[scen] = mre['MEWG']
                raw_mewk[scen] = mre['MEWK']
                raw_FCO2[scen] = np.sum(np.array(mre['FCO2']), axis=1)
                raw_RCO2[scen] = np.sum(np.array(mre['FCO2']), axis=0)
                raw_metc[scen] = mre['METC']
                raw_mewc[scen] = mre['MEWC']
                raw_rgdp[scen] = np.array(mre['RGDP'])[0] #  Weigh variables by RGDP
                raw_fret[scen] = np.sum(np.array(mre['FRET']), axis=1) # Information about individual energy sources not relevant
                raw_kre[scen] = np.array(mre['KR'])[:, 21, :] # Investment in new generation capacity (2010 mEuro)
                raw_mssp[scen] = mre['MSSP']
                raw_mlsp[scen] = mre['MLSP']    
                raw_mssm[scen] = mre['MSSM']
                raw_mlsm[scen] = mre['MLSM']
                raw_mewl[scen] = mre['MEWL']
                raw_tfec[scen] = np.sum(np.array(mre["TPED"]), axis=1)
                raw_mklb[scen] = mre['MKLB']   # Generation per load band
                raw_mewe[scen] = np.sum(np.array(mre["MEWE"]), axis=1)   # Emissions by technology
                
                raw_mwg1[scen] = mre['MWG1']   # Generation in LB1
                raw_mwg2[scen] = mre['MWG2']   # Generation in LB1
                raw_mwg3[scen] = mre['MWG3']   # Generation in LB1
                raw_mwg4[scen] = mre['MWG4']   # Generation in LB1
                raw_mwg5[scen] = mre['MWG5']   # Generation in LB1
                raw_mwg6[scen] = mre['MWG6']   # Generation in LB1

             
        
            for reg, inds in regs_to_print.items():
                
                share_ren, share_solar = data_per_region(raw_mewg, scen, inds)
                if "Baseline" in scenarios_to_print:
                    FCO2_ba = FCO2_ba + list(np.sum(raw_FCO2[scen][inds], axis=0) / np.sum(raw_FCO2['Baseline'][inds], axis=0))[y1:]
                FCO2_2010 = FCO2_2010 + \
                    list(np.sum(raw_FCO2[scen][inds], axis=0) / np.sum(raw_FCO2[scen][inds], axis=0)[0] *100)[y1:]
                mewg_ren_share = mewg_ren_share + share_ren[y1:]
                mewg_solar_share = mewg_solar_share + share_solar[y1:]
                
                mewe = mewe + list(np.sum(raw_mewe[scen][inds], axis=0))[y1:]             
                fret = fret + list(np.sum(raw_fret[scen][inds], axis=0))[y1:]
                tfec = tfec + list(np.sum(raw_tfec[scen][inds], axis=0))[y1:]
                kre_frac = kre_frac + list(np.sum(raw_kre[scen][inds], axis=0) / np.sum(raw_rgdp[scen][inds], axis=0)*100)[y1:]
                kre = kre + list(np.sum(raw_kre[scen][inds], axis=0)/1000)[y1:]
                kre_2019_benchmark = kre_2019_benchmark + \
                        list(np.sum(raw_kre[scen][inds], axis=0)/np.sum(raw_kre[scen][inds], axis=0)[9])[y1:]

                
                # Compute various LCOE values. Bare is without carbon tax or subsidies
                lcoe_solar = lcoe_solar + average_region(raw_metc, raw_mewg, scen, inds, 'solar')[y1:]
                lcoe_coal = lcoe_coal + average_region(raw_metc, raw_mewg, scen, inds, 'coal')[y1:]
                lcoe_gas = lcoe_gas + average_region(raw_metc, raw_mewg, scen, inds, 'gas')[y1:]
                lcoe_bare_solar = lcoe_bare_solar + average_region(raw_mewc, raw_mewg, scen, inds, 'solar')[y1:]
                lcoe_bare_nuclear = lcoe_bare_nuclear + average_region(raw_mewc, raw_mewg, scen, inds, 'nuclear')[y1:]
                lcoe_bare_coal = lcoe_bare_coal + average_region(raw_mewc, raw_mewg, scen, inds, 'coal')[y1:]
                lcoe_bare_gas = lcoe_bare_gas + average_region(raw_mewc, raw_mewg, scen, inds, 'gas')[y1:]
                lcoe_bare_hydro = lcoe_bare_hydro + average_region(raw_mewc, raw_mewg, scen, inds, 'hydro')[y1:]
                lcoe_bare_wind = lcoe_bare_wind + average_region(raw_mewc, raw_mewg, scen, inds, 'wind')[y1:]
                lcoe_bare_offshore = lcoe_bare_offshore + average_region(raw_mewc, raw_mewg, scen, inds, 'offshore wind')[y1:]

                # Compute how generation is divides over various load bands. 
                mwg1 = mwg1 + average_region(raw_mwg1, raw_mewg, scen, inds, 'coal')[y1:]
                mwg2 = mwg2 + average_region(raw_mwg2, raw_mewg, scen, inds, 'coal')[y1:]
                mwg3 = mwg3 + average_region(raw_mwg3, raw_mewg, scen, inds, 'coal')[y1:]
                mwg4 = mwg4 + average_region(raw_mwg4, raw_mewg, scen, inds, 'coal')[y1:]
                mwg5 = mwg5 + average_region(raw_mwg5, raw_mewg, scen, inds, 'coal')[y1:]
                mwg6 = mwg6 + average_region(raw_mwg6, raw_mewg, scen, inds, 'coal')[y1:]
                
                mwg_gas1 = mwg_gas1 + average_region(raw_mwg1, raw_mewg, scen, inds, 'gas')[y1:]
                mwg_gas2 = mwg_gas2 + average_region(raw_mwg2, raw_mewg, scen, inds, 'gas')[y1:]
                mwg_gas3 = mwg_gas3 + average_region(raw_mwg3, raw_mewg, scen, inds, 'gas')[y1:]
                mwg_gas4 = mwg_gas4 + average_region(raw_mwg4, raw_mewg, scen, inds, 'gas')[y1:]
                mwg_gas5 = mwg_gas5 + average_region(raw_mwg5, raw_mewg, scen, inds, 'gas')[y1:]
                mwg_gas6 = mwg_gas6 + average_region(raw_mwg6, raw_mewg, scen, inds, 'gas')[y1:]
                
                mewg_onshore = mewg_onshore + list(np.sum(np.array(raw_mewg[scen])[inds, var_dic['wind']], axis=0)[y1:])
                mewg_offshore = mewg_offshore + list(np.sum(np.array(raw_mewg[scen])[inds, var_dic['offshore wind']], axis=0)[y1:])


                
                # Create lists for the dataframe columns of characteristics (country, scenario, year)
                country = country + [reg]*len(share_ren[y1:])
                E3ME_region = E3ME_region + [inds] * len(share_ren[y1:])
                scenario_df = scenario_df + [scen]*len(share_ren[y1:])
                year = year + list(range(2010+y1, y3-y2))
    dt = 1
    
    #%% 
    df = pd.DataFrame()          # The main dataframe, with costs and shares


    df['Region']=country[::dt]
    df['E3ME region'] = E3ME_region[::dt]
    if "Baseline" in scenarios_to_print:
        df[r'CO$_2$ emissions w.r.t. baseline'] = FCO2_ba
    df[r'CO$_2$ emissions w.r.t. 2010'] = FCO2_2010
    df['Share solar'] = mewg_solar_share[::dt]
    df['Share renewables power'] = mewg_ren_share[::dt]
  
  
    #df['LCOE solar'] = lcoe_solar[::dt]
    #df['LCOE coal'] = lcoe_coal[::dt]
    #df['LCOE gas'] = lcoe_gas[::dt]
    
    df['LCOE coal'] = lcoe_bare_coal[::dt]
    df['LCOE gas'] = lcoe_bare_gas[::dt]
    df['LCOE hydro'] = lcoe_bare_hydro[::dt]
    df["LCOE nuclear"] = lcoe_bare_nuclear[::dt]
    df['LCOE onshore wind'] = lcoe_bare_wind[::dt]
    df['LCOE offshore wind'] = lcoe_bare_offshore[::dt]
    df['LCOE solar'] = lcoe_bare_solar[::dt]    
    
    df["Emissions"] = mewe[::dt]

    df['Scenario'] = scenario_df
    df['Year'] = year
    df["Investment"] = kre_frac
    df["Absolute investment"] = kre
    df["Investment wrt 2019 benchmark"] = kre_2019_benchmark
    df["Electricity demand"] = fret
    with np.errstate(divide='ignore', invalid='ignore'): 
        df["Electricity share"] = np.array(fret)/np.array(tfec)
    
    # Shares of technologies
    df_shares = pd.DataFrame()
    df_shares['Region'] = country[::dt]
    df_shares['Scenario'] = scenario_df
    df_shares['Year'] = year
    
    # Loadbands of dispatchable technologies (are they acting as baseload, or more flexible?)
    df_loadband = pd.DataFrame()
    df_loadband['Region'] = country[::dt]*2
    df_loadband['Scenario'] = scenario_df*2
    df_loadband['Year'] = year*2
    df_loadband["Gas or coal"] = ["Coal"]*len(year) + ["Gas"]*len(year)
    
    # Also convert from GWh to TWh
    df_loadband["Baseload"] = list(np.array(mwg1)/1000) + list(np.array(mwg_gas1)/1000)
    df_loadband["Lower mid-load "] = list(np.array(mwg2)/1000) + list(np.array(mwg_gas2)/1000)
    df_loadband["Upper mid-load"] = list(np.array(mwg3)/1000) + list(np.array(mwg_gas3)/1000)
    df_loadband["Peak load"] = list(np.array(mwg4 + mwg_gas4)/1000)
    df_loadband["Spare capacity"] = list(np.array(mwg5 + mwg_gas5)/1000)
    
    df_capacity = pd.DataFrame()
    years_once = list(range(2010+y1, y3-y2))
    df_capacity["Year"] = list(range(2010+y1, y3-y2)) * 3
    df_capacity["Technology"] = ["Solar"] * len(years_once) + ["Onshore wind"] * len(years_once) + ["Offshore wind"] * len(years_once)
    for reg, inds in regs_to_print.items():
        if reg != "Global":
            df_capacity[reg] = mewk_share(raw_mewk, scen, inds)[::dt]
            
    df_generation = pd.DataFrame()
    df_generation['Region'] = country[::dt]
    df_generation['Scenario'] = scenario_df
    df_generation['Year'] = year
    df_generation['Generation onshore wind'] = mewg_onshore[::dt]
    df_generation['Generation offshore wind'] = mewg_offshore[::dt]
        
    for tech in range(24):
        shares_list = []
        for scen in scenarios_to_print:
            for reg, inds in regs_to_print.items():
                shares, technology = tech_per_region(raw_mewg, scen, inds, tech)
                if technology != "Elsewhere aggregated":
                    shares_list = shares_list + shares[y1:]
              
        if technology != "Elsewhere aggregated":
             df_shares[technology] = shares_list
             
             
    #%%
    if print_temperature:
        # Printing total CO2 emissions since 2005 (to calculate temperature rise)
        # Note that data is only available between 2010 and 2060, so have
        # done extremely crude extrapolation
        for scen in scenarios_to_print:
            print(r'Total CO$_2$ emissions ' + scen)
            tot = np.sum(raw_FCO2[scen]) + 5*np.sum(raw_FCO2[scen][:, 0]) + 40*np.sum(raw_FCO2[scen][:, -1])
            print(f'{tot:.3e} ')
             
             
    return df, df_shares, df_loadband, df_capacity, df_generation
