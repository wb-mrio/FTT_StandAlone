# -*- coding: utf-8 -*-
"""
Created on Wed Aug 10

@author: sg
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy

import celib
# help(celib)

from celib import DB1, MRE, fillmat as fm
from numpy import nan
import os

dbpath = os.path.join('C:\\', 'E3ME', 'Master_Ortec_Updates', 'databank', 'U.db1')
mrepath = os.path.join('C:\\', 'E3ME', 'Master_Ortec_Updates', 'Output', 'Dan_ba.mre')
inpath = os.path.join('C:\\', 'E3ME', 'FTT_Stand_Alone', 'Inputs', 'IUD Update')
outpath = os.path.join('C:\\', 'E3ME', 'FTT_Stand_Alone', 'Inputs', 'IUD Update' , 'new')
outpath2 = os.path.join('C:\\', 'E3ME', 'FTT_Stand_Alone', 'Inputs', 'S0')


if __name__ == '__main__':
    with DB1(dbpath) as dbu:
        regions = dbu['RTI']
        regions_short = dbu['RSHORTTI']
        industries = dbu['YTI']
        cti = dbu['CTI']
        fuel_users = dbu['FUTI'] #titles of fuel users
        fuel_types = dbu['JTI'] #titles of fuel types
        erti = dbu['ERTI'] # titles of FTT resources classification
        mti = dbu['MTI'] # titles of import groups
        t2ti = dbu['T2TI'] #titles of FTT energy technologies
        c2ti = dbu['C2TI'] #titles of cost catagories
        
    years = range(2010, 2061)

    # Region and sectors (E3ME regions EU28)
    region_list = ['AT','BE','BG','CY','CZ','DE','DK','EN','EL','ES','FI','FR',
                    'HR','HU','IE','IT','LT','LX','LV','MT','NL','PL','PT','RO','SW','SI','SK','UK']
    
    sectors = ['CHI', 'FBT', 'MTM', 'NMM', 'OIS2']
    sectornumber = ['1','2','3','4','5']
    sector_conversion = {
        'CHI': ['6 Chemicals'],
        'FBT': ['9 Food, drink & tob.'],
        'MTM': ['12 Engineering etc', '5 Non-ferrous metals', '15 Rail transport', '16 Road transport', '17 Air transport', '18 Other transp. serv.'],
        'NMM': ['7 Non-metallics nes'],
        'OIS': ['13 Other industry', '11 Paper & pulp','10 Tex., cloth. & footw.'],
        }

    
    #1. Read in old IUD data
    iud = {}
    for sn in sectornumber:
        iud[sn]={}
        for r in region_list:
            iud[sn][r]={}
            if sn == '1':
                iud[sn][r] = pd.read_csv(inpath +'\\FTT-IH-' + 'CHI' + '\\IUD' + sn + '_' + r +'.csv', index_col = 0, skiprows = None)
            if sn == '2':
                iud[sn][r] = pd.read_csv(inpath +'\\FTT-IH-' + 'FBT' + '\\IUD' + sn + '_' + r +'.csv', index_col = 0, skiprows = None)
            if sn == '3':
                iud[sn][r] = pd.read_csv(inpath +'\\FTT-IH-' + 'MTM' + '\\IUD' + sn + '_' + r +'.csv', index_col = 0, skiprows = None)
            if sn == '4':
                iud[sn][r] = pd.read_csv(inpath +'\\FTT-IH-' + 'NMM' + '\\IUD' + sn + '_' + r +'.csv', index_col = 0, skiprows = None)
            if sn == '5':
                iud[sn][r] = pd.read_csv(inpath +'\\FTT-IH-' + 'OIS2' + '\\IUD' + sn + '_' + r +'.csv', index_col = 0, skiprows = None)
                  
    
    
    #2. Replace 2016 onwards with NANs
    for sn in sectornumber:
        for r in  region_list:
            for x in range(46,91):
                iud[sn][r].iloc[:,x] = nan
    
    #3. Read in FR from E3ME and aggregate to broader fuels
    
    FRCT={}
    FR02={}
    FROT={}
    FR03={}
    FR05={}
    FRET={}
    FRGT={}
    FRBT={}
    FR={}
    FR06={}
    FR09={}
    
    with MRE(mrepath) as mre:
        for r,reg in enumerate(regions_short):
            if reg in region_list:
                FR09[reg] = pd.DataFrame(mre['FR09'][r], index=fuel_users, columns=years)
                FR06[reg] = pd.DataFrame(mre['FR06'][r], index=fuel_users, columns=years)
                FRCT[reg] = pd.DataFrame(mre['FRCT'][r], index=fuel_users, columns=years) #Carbon use
                FR02[reg] = pd.DataFrame(mre['FR02'][r], index=fuel_users, columns=years)
                FROT[reg] = pd.DataFrame(mre['FROT'][r], index=fuel_users, columns=years)
                FR03[reg] = pd.DataFrame(mre['FR03'][r], index=fuel_users, columns=years)
                FR05[reg] = pd.DataFrame(mre['FR05'][r], index=fuel_users, columns=years)
                FRET[reg] = pd.DataFrame(mre['FRET'][r], index=fuel_users, columns=years)
                FRGT[reg] = pd.DataFrame(mre['FRGT'][r], index=fuel_users, columns=years)
                FRBT[reg] = pd.DataFrame(mre['FRBT'][r], index=fuel_users, columns=years)
                
    coal, oil, gas, electricity, biomass, steam_distributed = {}, {}, {}, {}, {}, {}
    
    for r in region_list:
        coal[r], oil[r], gas[r], electricity[r], biomass[r], steam_distributed[r] = {}, {}, {}, {}, {}, {}
        for sec in sector_conversion:
            coal[r][sec], oil[r][sec], gas[r][sec], electricity[r][sec], biomass[r][sec], steam_distributed[r][sec] = {}, {}, {}, {}, {}, {}
    

    
    for r,reg in enumerate(regions_short):
        if reg in region_list:          
            coal[reg]['OIS'] = (FR02[reg].loc['13 Other industry']+FR02[reg].loc['11 Paper & pulp']+FR02[reg].loc['10 Tex., cloth. & footw.'])\
                                +(FRCT[reg].loc['13 Other industry']+FRCT[reg].loc['11 Paper & pulp']+FRCT[reg].loc['10 Tex., cloth. & footw.'])
            
            coal[reg]['CHI'] = FR02[reg].loc['6 Chemicals']+FRCT[reg].loc['6 Chemicals']
            
            coal[reg]['FBT'] = FR02[reg].loc['9 Food, drink & tob.']+FRCT[reg].loc['9 Food, drink & tob.']
            
            coal[reg]['MTM'] = (FR02[reg].loc['12 Engineering etc']+FR02[reg].loc['5 Non-ferrous metals']+FR02[reg].loc['15 Rail transport']\
                                +FR02[reg].loc['16 Road transport']+FR02[reg].loc['17 Air transport']+FR02[reg].loc['18 Other transp. serv.'])\
                                +(FRCT[reg].loc['12 Engineering etc']+FRCT[reg].loc['5 Non-ferrous metals']+FRCT[reg].loc['15 Rail transport']\
                                  +FRCT[reg].loc['16 Road transport']+FRCT[reg].loc['17 Air transport']+FRCT[reg].loc['18 Other transp. serv.'])
            
            coal[reg]['NMM'] = FR02[reg].loc['7 Non-metallics nes']+FRCT[reg].loc['7 Non-metallics nes']
            
       
    for r,reg in enumerate(regions_short):
        if reg in region_list:          
            oil[reg]['OIS'] = (FROT[reg].loc['13 Other industry']+FROT[reg].loc['11 Paper & pulp']+FROT[reg].loc['10 Tex., cloth. & footw.'])\
                                +(FR03[reg].loc['13 Other industry']+FR03[reg].loc['11 Paper & pulp']+FR03[reg].loc['10 Tex., cloth. & footw.'])\
                                +(FR05[reg].loc['13 Other industry']+FR05[reg].loc['11 Paper & pulp']+FR05[reg].loc['10 Tex., cloth. & footw.'])
            
            oil[reg]['CHI'] = FROT[reg].loc['6 Chemicals']+FR03[reg].loc['6 Chemicals']+FR05[reg].loc['6 Chemicals']
            
            oil[reg]['FBT'] = FROT[reg].loc['9 Food, drink & tob.']+FR03[reg].loc['9 Food, drink & tob.']+FR05[reg].loc['9 Food, drink & tob.']
            
            oil[reg]['MTM'] = (FROT[reg].loc['12 Engineering etc']+FROT[reg].loc['5 Non-ferrous metals']+FROT[reg].loc['15 Rail transport']\
                                +FROT[reg].loc['16 Road transport']+FROT[reg].loc['17 Air transport']+FROT[reg].loc['18 Other transp. serv.'])\
                                +(FR03[reg].loc['12 Engineering etc']+FR03[reg].loc['5 Non-ferrous metals']+FR03[reg].loc['15 Rail transport']\
                                  +FR03[reg].loc['16 Road transport']+FR03[reg].loc['17 Air transport']+FR03[reg].loc['18 Other transp. serv.'])\
                                  +(FR05[reg].loc['12 Engineering etc']+FR05[reg].loc['5 Non-ferrous metals']+FR05[reg].loc['15 Rail transport']\
                                  +FR05[reg].loc['16 Road transport']+FR05[reg].loc['17 Air transport']+FR05[reg].loc['18 Other transp. serv.'])\
                                    
            oil[reg]['NMM'] = FROT[reg].loc['7 Non-metallics nes']+FR03[reg].loc['7 Non-metallics nes']+FR05[reg].loc['7 Non-metallics nes']
        
    for r,reg in enumerate(regions_short):
        if reg in region_list:          
            gas[reg]['OIS'] = (FR06[reg].loc['13 Other industry']+FR06[reg].loc['11 Paper & pulp']+FR06[reg].loc['10 Tex., cloth. & footw.'])\
                                +(FRGT[reg].loc['13 Other industry']+FRGT[reg].loc['11 Paper & pulp']+FRGT[reg].loc['10 Tex., cloth. & footw.'])
            
            gas[reg]['CHI'] = FR06[reg].loc['6 Chemicals']+FRGT[reg].loc['6 Chemicals']
            
            gas[reg]['FBT'] = FR06[reg].loc['9 Food, drink & tob.']+FRGT[reg].loc['9 Food, drink & tob.']
            
            gas[reg]['MTM'] = (FR06[reg].loc['12 Engineering etc']+FR06[reg].loc['5 Non-ferrous metals']+FR06[reg].loc['15 Rail transport']\
                                +FR06[reg].loc['16 Road transport']+FR06[reg].loc['17 Air transport']+FR06[reg].loc['18 Other transp. serv.'])\
                                +(FRGT[reg].loc['12 Engineering etc']+FRGT[reg].loc['5 Non-ferrous metals']+FRGT[reg].loc['15 Rail transport']\
                                  +FRGT[reg].loc['16 Road transport']+FRGT[reg].loc['17 Air transport']+FRGT[reg].loc['18 Other transp. serv.'])
            
            gas[reg]['NMM'] = FR06[reg].loc['7 Non-metallics nes']+FRGT[reg].loc['7 Non-metallics nes']
            
    for r,reg in enumerate(regions_short):
        if reg in region_list:          
            electricity[reg]['OIS'] = (FRET[reg].loc['13 Other industry']+FRET[reg].loc['11 Paper & pulp']+FRET[reg].loc['10 Tex., cloth. & footw.'])
            
            electricity[reg]['CHI'] = FRET[reg].loc['6 Chemicals']
            
            electricity[reg]['FBT'] = FRET[reg].loc['9 Food, drink & tob.']
            
            electricity[reg]['MTM'] = (FRET[reg].loc['12 Engineering etc']+FRET[reg].loc['5 Non-ferrous metals']+FRET[reg].loc['15 Rail transport']\
                                +FRET[reg].loc['16 Road transport']+FRET[reg].loc['17 Air transport']+FRET[reg].loc['18 Other transp. serv.'])
                                
            electricity[reg]['NMM'] = FRET[reg].loc['7 Non-metallics nes']
            
    for r,reg in enumerate(regions_short):
        if reg in region_list:          
            biomass[reg]['OIS'] = (FRBT[reg].loc['13 Other industry']+FRBT[reg].loc['11 Paper & pulp']+FRBT[reg].loc['10 Tex., cloth. & footw.'])
            
            biomass[reg]['CHI'] = FRBT[reg].loc['6 Chemicals']
            
            biomass[reg]['FBT'] = FRBT[reg].loc['9 Food, drink & tob.']
            
            biomass[reg]['MTM'] = (FRBT[reg].loc['12 Engineering etc']+FRBT[reg].loc['5 Non-ferrous metals']+FRBT[reg].loc['15 Rail transport']\
                                +FRBT[reg].loc['16 Road transport']+FRBT[reg].loc['17 Air transport']+FRBT[reg].loc['18 Other transp. serv.'])
                                
            biomass[reg]['NMM'] = FRBT[reg].loc['7 Non-metallics nes']
        
    for r,reg in enumerate(regions_short):
        if reg in region_list:          
            steam_distributed[reg]['OIS'] = (FR09[reg].loc['13 Other industry']+FR09[reg].loc['11 Paper & pulp']+FR09[reg].loc['10 Tex., cloth. & footw.'])
            
            steam_distributed[reg]['CHI'] = FR09[reg].loc['6 Chemicals']
            
            steam_distributed[reg]['FBT'] = FR09[reg].loc['9 Food, drink & tob.']
            
            steam_distributed[reg]['MTM'] = (FR09[reg].loc['12 Engineering etc']+FR09[reg].loc['5 Non-ferrous metals']+FR09[reg].loc['15 Rail transport']\
                                +FR09[reg].loc['16 Road transport']+FR09[reg].loc['17 Air transport']+FR09[reg].loc['18 Other transp. serv.'])
                                
            steam_distributed[reg]['NMM'] = FR09[reg].loc['7 Non-metallics nes']
            
            
    # 4. Fill with growth rates

    iud_fm = copy.deepcopy(iud)
    for sn in sectornumber:
        for reg in region_list:
            iud_fm[sn][reg] = iud_fm[sn][reg].iloc[:,40:91] 
            
    for r,reg in enumerate(regions_short):
        if reg in region_list:  
            iud_fm['5'][reg].loc['Direct Heating Coal'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Direct Heating Coal'], coal[reg]['OIS'])
            iud_fm['5'][reg].loc['Indirect Heating Coal'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Indirect Heating Coal'], coal[reg]['OIS'])
            iud_fm['5'][reg].loc['Indirect Heating Oil'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Indirect Heating Oil'], oil[reg]['OIS'])
            iud_fm['5'][reg].loc['Indirect Heating Gas'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Indirect Heating Gas'], gas[reg]['OIS'])
            iud_fm['5'][reg].loc['Indirect Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Indirect Heating Biomass'], biomass[reg]['OIS'])
            iud_fm['5'][reg].loc['Indirect Heating Electric'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Indirect Heating Electric'], electricity[reg]['OIS'])
            iud_fm['5'][reg].loc['Indirect Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Indirect Heating Steam Distributed'], steam_distributed[reg]['OIS'])
            iud_fm['5'][reg].loc['Heat Pumps (Electricity)'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Heat Pumps (Electricity)'], electricity[reg]['OIS'])
            iud_fm['5'][reg].loc['Direct Heating Oil'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Direct Heating Oil'], oil[reg]['OIS'])
            iud_fm['5'][reg].loc['Direct Heating Gas'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Direct Heating Gas'], gas[reg]['OIS'])
            iud_fm['5'][reg].loc['Direct Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Direct Heating Biomass'], biomass[reg]['OIS'])
            iud_fm['5'][reg].loc['Direct Heating Electric'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Direct Heating Electric'], electricity[reg]['OIS'])
            iud_fm['5'][reg].loc['Direct Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['5'][reg].loc['Direct Heating Steam Distributed'], steam_distributed[reg]['OIS'])
    
    for r,reg in enumerate(regions_short):
        if reg in region_list:  
            iud_fm['1'][reg].loc['Direct Heating Coal'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Direct Heating Coal'], coal[reg]['CHI'])
            iud_fm['1'][reg].loc['Indirect Heating Coal'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Indirect Heating Coal'], coal[reg]['CHI'])
            iud_fm['1'][reg].loc['Indirect Heating Oil'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Indirect Heating Oil'], oil[reg]['CHI'])
            iud_fm['1'][reg].loc['Indirect Heating Gas'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Indirect Heating Gas'], gas[reg]['CHI'])
            iud_fm['1'][reg].loc['Indirect Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Indirect Heating Biomass'], biomass[reg]['CHI'])
            iud_fm['1'][reg].loc['Indirect Heating Electric'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Indirect Heating Electric'], electricity[reg]['CHI'])
            iud_fm['1'][reg].loc['Indirect Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Indirect Heating Steam Distributed'], steam_distributed[reg]['CHI'])
            iud_fm['1'][reg].loc['Heat Pumps (Electricity)'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Heat Pumps (Electricity)'], electricity[reg]['CHI'])
            iud_fm['1'][reg].loc['Direct Heating Oil'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Direct Heating Oil'], oil[reg]['CHI'])
            iud_fm['1'][reg].loc['Direct Heating Gas'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Direct Heating Gas'], gas[reg]['CHI'])
            iud_fm['1'][reg].loc['Direct Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Direct Heating Biomass'], biomass[reg]['CHI'])
            iud_fm['1'][reg].loc['Direct Heating Electric'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Direct Heating Electric'], electricity[reg]['CHI'])
            iud_fm['1'][reg].loc['Direct Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['1'][reg].loc['Direct Heating Steam Distributed'], steam_distributed[reg]['CHI'])
    
    for r,reg in enumerate(regions_short):
        if reg in region_list:  
            iud_fm['2'][reg].loc['Direct Heating Coal'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Direct Heating Coal'], coal[reg]['FBT'])
            iud_fm['2'][reg].loc['Indirect Heating Coal'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Indirect Heating Coal'], coal[reg]['FBT'])
            iud_fm['2'][reg].loc['Indirect Heating Oil'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Indirect Heating Oil'], oil[reg]['FBT'])
            iud_fm['2'][reg].loc['Indirect Heating Gas'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Indirect Heating Gas'], gas[reg]['FBT'])
            iud_fm['2'][reg].loc['Indirect Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Indirect Heating Biomass'], biomass[reg]['FBT'])
            iud_fm['2'][reg].loc['Indirect Heating Electric'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Indirect Heating Electric'], electricity[reg]['FBT'])
            iud_fm['2'][reg].loc['Indirect Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Indirect Heating Steam Distributed'], steam_distributed[reg]['FBT'])
            iud_fm['2'][reg].loc['Heat Pumps (Electricity)'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Heat Pumps (Electricity)'], electricity[reg]['FBT'])
            iud_fm['2'][reg].loc['Direct Heating Oil'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Direct Heating Oil'], oil[reg]['FBT'])
            iud_fm['2'][reg].loc['Direct Heating Gas'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Direct Heating Gas'], gas[reg]['FBT'])
            iud_fm['2'][reg].loc['Direct Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Direct Heating Biomass'], biomass[reg]['FBT'])
            iud_fm['2'][reg].loc['Direct Heating Electric'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Direct Heating Electric'], electricity[reg]['FBT'])
            iud_fm['2'][reg].loc['Direct Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['2'][reg].loc['Direct Heating Steam Distributed'], steam_distributed[reg]['FBT'])
    
    for r,reg in enumerate(regions_short):
        if reg in region_list:  
            iud_fm['3'][reg].loc['Direct Heating Coal'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Direct Heating Coal'], coal[reg]['MTM'])
            iud_fm['3'][reg].loc['Indirect Heating Coal'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Indirect Heating Coal'], coal[reg]['MTM'])
            iud_fm['3'][reg].loc['Indirect Heating Oil'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Indirect Heating Oil'], oil[reg]['MTM'])
            iud_fm['3'][reg].loc['Indirect Heating Gas'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Indirect Heating Gas'], gas[reg]['MTM'])
            iud_fm['3'][reg].loc['Indirect Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Indirect Heating Biomass'], biomass[reg]['MTM'])
            iud_fm['3'][reg].loc['Indirect Heating Electric'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Indirect Heating Electric'], electricity[reg]['MTM'])
            iud_fm['3'][reg].loc['Indirect Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Indirect Heating Steam Distributed'], steam_distributed[reg]['MTM'])
            iud_fm['3'][reg].loc['Heat Pumps (Electricity)'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Heat Pumps (Electricity)'], electricity[reg]['MTM'])
            iud_fm['3'][reg].loc['Direct Heating Oil'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Direct Heating Oil'], oil[reg]['MTM'])
            iud_fm['3'][reg].loc['Direct Heating Gas'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Direct Heating Gas'], gas[reg]['MTM'])
            iud_fm['3'][reg].loc['Direct Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Direct Heating Biomass'], biomass[reg]['MTM'])
            iud_fm['3'][reg].loc['Direct Heating Electric'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Direct Heating Electric'], electricity[reg]['MTM'])
            iud_fm['3'][reg].loc['Direct Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['3'][reg].loc['Direct Heating Steam Distributed'], steam_distributed[reg]['MTM'])
    
    for r,reg in enumerate(regions_short):
        if reg in region_list:  
            iud_fm['4'][reg].loc['Direct Heating Coal'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Direct Heating Coal'], coal[reg]['NMM'])
            iud_fm['4'][reg].loc['Indirect Heating Coal'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Indirect Heating Coal'], coal[reg]['NMM'])
            iud_fm['4'][reg].loc['Indirect Heating Oil'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Indirect Heating Oil'], oil[reg]['NMM'])
            iud_fm['4'][reg].loc['Indirect Heating Gas'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Indirect Heating Gas'], gas[reg]['NMM'])
            iud_fm['4'][reg].loc['Indirect Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Indirect Heating Biomass'], biomass[reg]['NMM'])
            iud_fm['4'][reg].loc['Indirect Heating Electric'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Indirect Heating Electric'], electricity[reg]['NMM'])
            iud_fm['4'][reg].loc['Indirect Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Indirect Heating Steam Distributed'], steam_distributed[reg]['NMM'])
            iud_fm['4'][reg].loc['Heat Pumps (Electricity)'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Heat Pumps (Electricity)'], electricity[reg]['NMM'])
            iud_fm['4'][reg].loc['Direct Heating Oil'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Direct Heating Oil'], oil[reg]['NMM'])
            iud_fm['4'][reg].loc['Direct Heating Gas'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Direct Heating Gas'], gas[reg]['NMM'])
            iud_fm['4'][reg].loc['Direct Heating Biomass'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Direct Heating Biomass'], biomass[reg]['NMM'])
            iud_fm['4'][reg].loc['Direct Heating Electric'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Direct Heating Electric'], electricity[reg]['NMM'])
            iud_fm['4'][reg].loc['Direct Heating Steam Distributed'] = fm.fill_with_growth_rates(iud_fm['4'][reg].loc['Direct Heating Steam Distributed'], steam_distributed[reg]['NMM'])
    

    # Append or concat iud_fm to iud_back
    iud_back = copy.deepcopy(iud)
    for sn in sectornumber:
        for reg in region_list:
            iud_back[sn][reg] = iud_back[sn][reg].iloc[:,0:40]
            
    iud_final={}     
    for sn in sectornumber:
        iud_final[sn]={}
        for r in region_list:
            iud_final[sn][r]={}
      
    for sn in sectornumber:
        for r in region_list:
            iud_final[sn][r] = pd.concat([iud_back[sn][r], iud_fm[sn][r]], axis=1)
    
    
    # 5. Export
    for sn in sectornumber:
        for r in region_list:
            if sn == '1':
                iud_final[sn][r].to_csv(os.path.join(outpath, 'FTT-IH-CHI') + '\\'+ 'IUD' + sn + '_' + r + '.csv')
            if sn == '2':
                iud_final[sn][r].to_csv(os.path.join(outpath, 'FTT-IH-FBT') + '\\'+ 'IUD' + sn + '_' + r + '.csv')
            if sn == '3':
                iud_final[sn][r].to_csv(os.path.join(outpath, 'FTT-IH-MTM') + '\\'+ 'IUD' + sn + '_' + r + '.csv')
            if sn == '4':
                iud_final[sn][r].to_csv(os.path.join(outpath, 'FTT-IH-NMM') + '\\'+ 'IUD' + sn + '_' + r + '.csv')
            if sn == '5':
                iud_final[sn][r].to_csv(os.path.join(outpath, 'FTT-IH-OIS2') + '\\'+ 'IUD' + sn + '_' + r + '.csv')
                       