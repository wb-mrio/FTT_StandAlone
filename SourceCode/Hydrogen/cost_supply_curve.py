# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 03:02:18 2025

@author: pv
"""

# Standard library imports
from math import sqrt
import copy
import warnings

# Third party imports
import numpy as np

# Local library imports
from SourceCode.support.divide import divide
from SourceCode.Hydrogen.ftt_h2_lcoh import get_lcoh as get_lcoh2
from SourceCode.Hydrogen.ftt_h2_csc import get_csc
from SourceCode.Hydrogen.ftt_h2_pooledtrade import pooled_trade
from SourceCode.core_functions.substitution_frequencies import sub_freq



def calc_csc(lc, lc_sd, demand, capacity, capacity_factor, transport_cost, titles, bins=500):
    
    # Categories for the cost matrix (BHTC)
    c7ti = {category: index for index, category in enumerate(titles['C7TI'])}
    jti = {category: index for index, category in enumerate(titles['JTI'])}
    hyti = {category: index for index, category in enumerate(titles['HYTI'])}
    
    # Initialise a 3D variable
    lc_erf = np.zeros([bins, len(titles['RTI']), len(titles['HYTI'])])
    
    cf_limit = 1.0 + 0.4*(1.0 - capacity_factor[:, :, 0])
    capacity_online = capacity[:, :, 0] * cf_limit
    
    # Estimate the weigthed transportation costs
    # From the perspective of the exporter
    weighted_tc_exp = np.divide(transport_cost[:, :, 0] * demand[:, 0, 0],
                                demand[:, 0, 0].sum())
    # From the perspective of the importer
    weighted_tc_imp = np.divide(
        np.multiply(transport_cost[:, :, 0], demand[None, :, 0, 0]),
        demand[:, 0, 0].sum()).sum(axis=0)
    
    # Min and max lcoh2
    lc_min = np.min(lc[:, :, 0] - 3 * lc_sd[:, :, 0] + weighted_tc_imp[:, None])
    lc_max = np.max(lc[:, :, 0] + 3 * lc_sd[:, :, 0] + weighted_tc_imp[:, None]) 
    
    # Cost spacing of the bins
    cost_space = np.linspace(lc_min, lc_max, bins)
    
    # Regional CSC
    for r in range(len(titles['RTI'])):
        
        for i in range(len(titles['HYTI'])):
        
            mu = lc[r, i, 0]
            sigma = lc_sd[r, i, 0] * mu
            cap = capacity_online[r, i]
            lc_erf[:, r, i] = cap * (0.5 + 0.5 * np.tanh(1.25*(cost_space-mu)/sigma))
            
    # Collapse the regional CSC into one global CSC
    glo_csc = lc_erf.sum(axis=1).sum(axis=1)
    
    # Check is there is sufficient supply
    if glo_csc[-1] > demand[:, 0, 0].sum():
        
        # Find the index of the minimum value in absolute terms after 
        # subtracting global demand
        idx = np.argmin(np.abs(glo_csc - demand[:, 0, 0].sum()))
        
        # Import price 
        hy_price =  glo_csc[idx]
        
    else:
        
        # Take the last bin
        idx = bins-1
        
        # Import price 
        hy_price =  glo_csc[idx]
        
    # Now use the found price to see which technologies and regions are exporters
    production = lc_erf[idx, :, :]
    capacity_factor_new = divide(production, capacity[:, :, 0])
    
    return production, hy_price, capacity_factor_new
    
    
    
        
        
    
    
    