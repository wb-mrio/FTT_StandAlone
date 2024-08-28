# -*- coding: utf-8 -*-
"""
Created on Fri Jul 12 15:32:26 2024

@author: Femke Nijsse

Heat pump mandates. We dictate exogenous sales to be proportional
to historical generation. 

"""

import numpy as np

def heat_pump_mandate(heat_mandate, hwsa, hews, hewi_lag, year, n_years=11):
    """ 
    Sets a mandate which increasing to 80% of sales in 2035. That year, fossil
    fuel boilers are outregulated. The shares of each type of heat pump is
    proportional to historical shares. Similarly, the shares of lost fossil-based
    boilers is proportional to shares in previous year. 
    
    A few exceptions:
        * When this decreases growth HPs, use endogenous shares
        * When not enough fossil boilers are left, decrease mandate
    """
    
    
    fossil_techs = [0, 1, 2, 3, 6, 8]
    heat_pump_techs = [9, 10, 11]
    
    
    if heat_mandate[0,0,0] == 1:
        if year in range(2025, 2025 + n_years):
        
            n = year - 2024
            yearly_replacements = 1/20
            x = n / n_years
            exogenous_sigmoid = x / (x + 0.8)
            
            # In 2035, the sum should be 70% of sales are heat pump (as quite some endogenous sales). Lifetime = 20y, so 0.05 ~= 100%
            sum_hwsa = np.full(hwsa.shape[0], exogenous_sigmoid * yearly_replacements)   
            
            sum_ff = np.sum(hews[:, fossil_techs], axis=(1, 2))
            sum_hp = np.sum(hews[:, heat_pump_techs], axis=(1, 2))
            sum_hwsa = np.where(sum_ff < 1.8 * sum_hwsa, 0, sum_hwsa)          # Stop when there is too little fossil fuels to replace
            sum_hwsa = np.where(sum_hp > 1 - 2 * sum_hwsa, 0, sum_hwsa)        # Also stop if virtually all shares are heat pumps already
            
            # Compute fractions for each heat pump, ff technique, based on fraction of shares
            # Ensure no division by zero (note, fossil fuel second option doesn' matter, as we've already scaled sum_hwsa to sum_ff)
            backup_shares = np.tile(np.array([0.1, 0.45, 0.45]), (hwsa.shape[0], 1))
            frac_heat_pumps = np.where(sum_hp[:, None] > 0, hews[:, heat_pump_techs, 0] / sum_hp[:, None], backup_shares) 
            frac_fossils = np.where(sum_ff[:, None] > 0, hews[:, fossil_techs, 0] / sum_ff[:, None], hews[:, fossil_techs, 0])

            hwsa[:, fossil_techs, 0] = -sum_hwsa[:, None] * frac_fossils
            hwsa[:, heat_pump_techs, 0] = sum_hwsa[:, None] * frac_heat_pumps
            
            frac_hp_hewi = np.sum(hewi_lag[:, heat_pump_techs], axis=(1, 2))
        
            
            
    # Else: return hswa unchanged
    return hwsa
