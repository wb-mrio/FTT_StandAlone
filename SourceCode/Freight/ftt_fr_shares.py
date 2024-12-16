# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 12:59:07 2024

@author: Femke Nijsse
"""

import numpy as np


def shares(dt, t, no_it, zews_dt, zegc_dt, zttd_dt, zewa,
           turnover_rate, isReg, D, Utot, titles):

    num_regions = len(titles['RTI'])
    num_techs = len(titles['FTTI'])
    
    endo_shares = np.zeros((num_regions, num_techs))
    endo_capacity = np.zeros((num_regions, num_techs))
    
    for r in range(num_regions):
        if np.sum(D[r]) == 0.0:
            continue
        
        # Pairwise indices for b1, b2
        b1, b2 = np.triu_indices(num_techs, k=1)

        # Extract data for region r
        S_i = zews_dt[r, :, 0]  # shape: (num_techs,)
        Aik = zewa[0, b1, b2] * turnover_rate[r, b1]
        Aki = zewa[0, b2, b1] * turnover_rate[r, b1]
        dFik = np.sqrt(2) * np.sqrt(
            zttd_dt[r, b1, 0] ** 2 + zttd_dt[r, b2, 0] ** 2
        )
        Fik = 0.5 * (
            1 + np.tanh(
                1.25 * (zegc_dt[r, b2, 0] - zegc_dt[r, b1, 0]) / dFik
            )
        )

        # Mask for valid pairs
        skip_mask = skip_criteria(zews_dt, zegc_dt, zttd_dt, zewa, b1, b2, r)
        mask = ~skip_mask

        # Initialise F matrix
        F = np.ones((num_techs, num_techs)) * 0.5

        # Apply mask to preferences
        F[b1[mask], b2[mask]] = (
            Fik[mask] * (1.0 - isReg[r, b1[mask]]) * (1.0 - isReg[r, b2[mask]])
            + isReg[r, b2[mask]] * (1.0 - isReg[r, b1[mask]])
            + 0.5 * (isReg[r, b1[mask]] * isReg[r, b2[mask]])
        )
        F[b2[mask], b1[mask]] = (
            (1.0 - Fik[mask]) * (1.0 - isReg[r, b2[mask]]) * (1.0 - isReg[r, b1[mask]])
            + isReg[r, b1[mask]] * (1.0 - isReg[r, b2[mask]])
            + 0.5 * (isReg[r, b2[mask]] * isReg[r, b1[mask]])
        )

        # Runge-Kutta computations (masked)
        delta_F = Aik[mask] * F[b1[mask], b2[mask]] - Aki[mask] * F[b2[mask], b1[mask]]
        S_k = S_i[b2[mask]]
        S_i_pair = S_i[b1[mask]]

        k_1 = S_i_pair * S_k * delta_F
        k_2 = (S_i_pair + dt * k_1 / 2) * (S_k - dt * k_1 / 2) * delta_F
        k_3 = (S_i_pair + dt * k_2 / 2) * (S_k - dt * k_2 / 2) * delta_F
        k_4 = (S_i_pair + dt * k_3) * (S_k - dt * k_3) * delta_F

        # Accumulate dSik values
        dSik = np.zeros((num_techs, num_techs))
        dSik[b1[mask], b2[mask]] = dt * (k_1 + 2 * k_2 + 2 * k_3 + k_4) / 6
        dSik[b2[mask], b1[mask]] = -dSik[b1[mask], b2[mask]]

        # Update endogenous shares and capacity
        endo_shares[r] = S_i + np.sum(dSik, axis=1)
        endo_capacity[r] = endo_shares[r] * Utot[r]

    return endo_shares, endo_capacity




        
        
def implement_shares_policies(endo_capacity, endo_shares, 
                              titles, zwsa, zreg, isReg,
                              sum_over_classes, n_veh_classes, Utot, no_it):
        
    # Add in exogenous sales figures. These are blended with
    # endogenous result! Note that it's different from the
    # ExogSales specification!
    
    zews = np.zeros((len(titles['RTI']), len(titles['FTTI']), 1))

    
    for r in range(len(titles['RTI'])):
        
        dUk = np.zeros([len(titles['FTTI'])])
        dUkTK = np.zeros([len(titles['FTTI'])])
        dUkREG = np.zeros([len(titles['FTTI'])])
        
    
        # Check that exogenous sales additions aren't too large
        # As a proxy it can't be greater than 80% of the class fleet size
        # divided by 15 (the average lifetime of freight vehicles)
        sum_zwsa = sum_over_classes(zwsa)
        for veh_class in range(n_veh_classes):
            
            if sum_zwsa[r, veh_class, 0] > 0.8 * Utot[r, veh_class] / 15:
        
                # ZWSA_scalar[veh_class] = sum_zwsa[veh_class] / (0.8 * Utot[r] / 15)
                zwsa[r, veh_class::n_veh_classes] /= (
                                sum_zwsa[r, veh_class, 0] / (0.8 * Utot[r, veh_class] / 15) )
    
        # Check that exogenous capacity is smaller than regulated capacity
        # Regulations have priority over exogenous capacity
        reg_vs_exog = ((zwsa[r, :, 0] / no_it + endo_capacity[r]) 
                      > zreg[r, :, 0]) & (zreg[r, :, 0] >= 0.0)
     
        # ZWSA is yearly capacity additions. We need to split it up based on the number of time steps, and also scale it if necessary.
        dUkTK =  np.where(reg_vs_exog, 0.0, zwsa[r, :, 0] / no_it)
    
        # Correct for regulations due to the stretching effect. This is the difference in capacity due only to rflt increasing.
        # This is the difference between capacity based on the endogenous capacity, and what the endogenous capacity would have been
        # if rflz (i.e. total vehicles) had not grown.
        dUkREG = -(endo_capacity[r] - endo_shares[r] * Utot[r]) \
                 * isReg[r, :].reshape([len(titles['FTTI'])])
                                   
        # Sum effect of exogenous sales additions (if any) with effect of regulations. 
        dUk = dUkTK + dUkREG
        dUtot = [dUk[i::n_veh_classes].sum() for i in range(n_veh_classes)]
    
        # Calculate changes to endogenous capacity, and use to find new market shares
        # Zero capacity will result in zero shares
        # All other capacities will be streched
        for veh_class in range(n_veh_classes):
            denominator = (np.sum(endo_capacity[r, veh_class::n_veh_classes]) + dUtot[veh_class]) 
            if denominator > 0:
                zews[r, veh_class::n_veh_classes, 0] = ( 
                        (endo_capacity[r, veh_class::n_veh_classes] + dUk[veh_class::n_veh_classes])
                        / denominator )
    
            
    return zews




def skip_criteria(zews_dt, zegc_dt, zttd_dt, zewa, b1, b2, r):
    """Skip calculations when the shares, costs or std costs are zero.
    Also skip when the substitution is zero."""
    
    # Skip if starting shares are zero for tech b1
    condition_b1 = np.logical_and(
        zews_dt[r, b1, 0] > 0.0,
        np.logical_and(zegc_dt[r, b1, 0] != 0.0, zttd_dt[r, b1, 0] != 0.0)
    )
    
    # Skip if starting share or cost is zero for tech b2
    condition_b2 = np.logical_and(
        zews_dt[r, b2, 0] > 0.0,
        np.logical_and(zegc_dt[r, b2, 0] != 0.0, zttd_dt[r, b2, 0] != 0.0)
    )
    
    # Check if either b1 or b2 are zero for substitution
    condition_substitution = np.logical_or(
        zewa[0, b1, b2] != 0.0, zewa[0, b2, b1] != 0.0
    )
    
    # Return skip if any condition fails
    return np.logical_not(np.logical_and(condition_b1, np.logical_and(condition_b2, condition_substitution)))




def validate_shares(zews, sector, year, titles):
    for r in range(len(titles['RTI'])):
        if not (np.isclose(np.sum(zews[r, :, 0]), 5.0, atol=1e-5) or
                np.isclose(np.sum(zews[r, :, 0]), 4.0, atol=1e-5)):
            msg = (f"Sector: {sector} - Region: {titles['RTI'][r]} - Year: {year}"
            f"Sum of market shares do not add to 5.0 (instead: {np.sum(zews[r, :, 0])})")
            raise ValueError(msg)
    
        if np.any(zews[r, :, 0] < 0.0):
            msg = (f"Sector: {sector} - Region: {titles['RTI'][r]} - Year: {year}"
            "Negative market shares detected! Critical error!")
            raise ValueError(msg)

    return