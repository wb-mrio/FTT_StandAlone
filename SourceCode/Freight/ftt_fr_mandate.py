# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 11:13:09 2024

@author: Femke Nijsse
"""



import numpy as np

def EV_truck_mandate(EV_mandate, zwsa, zews, rflz, year, n_years=11):
    """ 
    Sets a mandate of growing exogenous sales to 2035. At that point, separately,
    regulations comes into play that outregulates fossil technologies. 
    
    A few exceptions:
        * When not enough fossil cars are left, no mandate
        * When there are too many EVs, no mandate
    """
    
    
    fossil_techs = [0, 2, 4, 6, 8]
    EV_techs = [12]
    
    
    if EV_mandate[0,0,0] == 1:
        if year in range(2030, 2030 + n_years):
        
            frac = 1/n_years            # Fraction decrease per year
            n = year - 2029
            
            yearly_replacement = 1/15 * 0.8
            
            # In 2035, the sum should be 80% of sales.
            sum_zwsa_share = np.full(zwsa.shape[0], frac * n * yearly_replacement)   
            
            sum_ff = np.sum(zews[:, fossil_techs], axis=(1, 2))
            sum_EV = np.sum(zews[:, EV_techs], axis=(1, 2))
            sum_zwsa = np.where(sum_ff < 1.8 * sum_zwsa_share, 0, sum_zwsa_share)          # Stop when there is too little fossil fuels to replace
            sum_zwsa = np.where(sum_EV > 1 - 2 * sum_zwsa_share, 0, sum_zwsa_share)        # Also stop if virtually all shares are heat pumps already
            
            # Compute fractions for each heat pump, ff technique, based on fraction of shares
            # Ensure no division by zero (note, fossil fuel second option doesn' matter, as we've already scaled sum_zwsa to sum_ff)
            backup_shares = np.tile(np.array([1.0]), (zwsa.shape[0], 1))
            # fraction of each EV type by region (backup_shares if dividing by zero)
            frac_EVs = np.divide(zews[:, EV_techs, 0],  sum_EV[:, None], out=backup_shares, where=sum_EV[:, None] > 0)
            frac_fossils =  np.divide(zews[:, fossil_techs, 0],  sum_ff[:, None])

            zwsa[:, fossil_techs, 0] = -sum_zwsa[:, None] * frac_fossils * rflz[:, :, 0]
            zwsa[:, EV_techs, 0] = sum_zwsa[:, None] * frac_EVs * rflz[:, :, 0]
            
            
            
    # Else: return hswa unchanged
    return zwsa
