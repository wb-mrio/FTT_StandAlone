# -*- coding: utf-8 -*-
"""
Created on Thu Feb 15 09:09:50 2024

@author: Cormac Lynch & Femke Nijsse
"""

import numpy as np

def get_sales(cap, cap_dt, cap_lag, shares, shares_dt, sales_or_investment_in, 
               timescales, dt):
    """
    Calculate new sales/investments for all FTT models (e.g. TEWI)

    1. If capacity has grown, the difference between the new capacity and the
       old.
    2. The amount of existing capacity that is depreciated (retired) as it
       reaches its end of life.
    
    Capacity depreciation is based on the technology lifetime in the
    cost matrix. 1/lifetime is depreciated each year.

    Parameters
    -----------
    cap: np.array
        Capacity (e.g. TEWK, MEWK)
    cap_dt: np.array
        Capacity at the previous timestep dt
    cap_lag: np.array
        Capacity at the previous year
    shares: np.array
        Current shares (e.g. TEWS, MEWS)
    shares_dt: np.array
        Shares at the previous timestep dt
    timescales: np.array
        Average lifetime of the various technologies
    dt: float
        dt is timestep: 1 / (number of timesteps).
    

    Returns
    ----------
    investment_or_sales: np.array
        investment or sales up to and including time t
    investment_or_sales_t: np.array
        investment or sales at time t
    
    """
    # Find capacity and share growth since last time step
    cap_growth = cap[:, :, 0] - cap_lag[:, :, 0]
    share_growth_dt = shares[:, :, 0] - shares_dt[:, :, 0]
    cap_growth_dt = cap[:, :, 0] - cap_dt[:, :, 0]

    # Calculate share_depreciation
    share_depreciation = shares_dt[:, :, 0] * dt / timescales
    
    # If there is growth, depreciation is fully replaced.
    # Where capacity has decreased, we only replace depreciated capacity
    # if the depreciation > capacity loss
    conditions = [
        (cap_growth >= 0.0),
        (-share_depreciation < share_growth_dt) & (share_growth_dt < 0)
    ]

    outputs_eol = [
        cap_dt[:, :, 0] * dt / timescales,
        (share_growth_dt + share_depreciation) * cap_lag[:, :, 0] 
    ]

    # Three end-of-life (eol) replacement options, depending on conditions
    eol_replacements = np.select(conditions, outputs_eol, default=0)
            
    # Ensure no negative values
    eol_replacements = np.maximum(eol_replacements, 0)
    eol_replacements = eol_replacements[:, :, np.newaxis]

    # Find total additions at time t
    # If capacity has grown, additions equal the difference +
    # eol replacements from the previous year.
    # Otherwise, additions just equal replacements.
    sales_dt = np.zeros(sales_or_investment_in.shape)
    sales_dt[:, :, 0] = np.where(cap_growth_dt[:, :] > 0.0,
                                cap_growth_dt[:, :] + eol_replacements[:, :, 0], 
                                eol_replacements[:, :, 0])
        
    # Add additions at iteration t to total annual additions
    sales_or_investment = sales_or_investment_in + sales_dt
    
    return sales_or_investment, sales_dt


def get_sales_yearly(cap, cap_lag, shares, shares_lag, sales_or_investment_in, timescales):
    """
    Calculate new sales/investments for all FTT models before simulation starts (e.g. TEWI)

    1. If capacity has grown, the difference between the new capacity and the
       old.
    2. The amount of existing capacity that is depreciated (retired) as it
       reaches its end of life.
    
    Capacity depreciation is based on the technology lifetime in the
    cost matrix. 1/lifetime is depreciated each year.

    Parameters
    -----------
    cap: np.array
        capacity (e.g. TEWK, MEWK)
    cap_lag: np.array
        capacity at the previous year
    shares: np.array
        current shares (e.g. TEWS, MEWS)
    shares_lag: np.array
        shares at the end of previous year
    timescales: np.array
        the average lifetime of the various technologies

    Returns
    ----------
    investment_or_sales: np.array
        investment or sales up to and including time t
    
    """
    # Find capacity and share growth since last year
    cap_growth = cap[:, :, 0] - cap_lag[:, :, 0]
    share_growth = shares[:, :, 0] - shares_lag[:, :, 0]

    # Calculate share_depreciation
    share_depreciation = shares_lag[:, :, 0] / timescales
    
    # If there is growth, end-of-life replacements take place fully
    # Where capacity has decreased, we only replace eol capacity
    # if the eol_replacement > capacity loss
    conditions = [
        (cap_growth >= 0.0),
        (-share_depreciation < share_growth) & (share_growth < 0)
    ]

    outputs = [
        cap_lag[:, :, 0] / timescales,
        (share_growth + share_depreciation) * cap_lag[:, :, 0]
    ]

    # Three end-of-life (eol) replacement options, depending on conditions
    eol_replacements = np.select(conditions, outputs, default=0)
            
    # Ensure no negative values
    eol_replacements = np.maximum(eol_replacements, 0)
    eol_replacements = eol_replacements[:, :, np.newaxis]

    # If capacity has grown, additions equal the difference +
    # eol replacement from the previous year.
    # Otherwise, additions just equal eol replacement.
    sales_or_investment = np.zeros((sales_or_investment_in.shape))
    sales_or_investment[:, :, 0] = np.where(cap_growth[:, :] > 0.0,
                                cap_growth[:, :] + eol_replacements[:, :, 0],
                                eol_replacements[:, :, 0])

    return sales_or_investment
