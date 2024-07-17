# -*- coding: utf-8 -*-
"""
=========================================
ftt_p_dspch.py
=========================================
Power generation dispatching FTT module.


Functions included:
    - dspch
        Calculate dispatching

"""

# Third party imports
import numpy as np
from numba import njit




# %% dispatch function
# -----------------------------------------------------------------------------
# -------------------------- DSPTCH of capacity ------------------------------
# -----------------------------------------------------------------------------
@njit(fastmath=True)
def dspch(MWDD, MEWS, MKLB, MCRT, MEWL, MWMC_lag, MMCD_lag, rti, t2ti, lbti):
    """
    Calculates dispatch of capacity.

    The function estimates an allocation of power production between
    technologies and load bands.

    Parameters
    -----------
    MWDD: NumPy array
        Matrix of load band tech suitability
    MEWS: NumPy array
        Market shares for the current year
    MKLB: NumPy array
        Capacity by load band
    MCRT: NumPy array
        Curtailment of VRE (% of generation)
    MEWL: NumPy array
        Load factors (%)
    MWMC_lag: NumPy array
        Lagged marginal costs
    MMCD_lag: NumPy array
        Lagged standard deviation of marginal costs
    rti: int
        Number of regions
    t2ti: int
        Number of technologies
    lbti: int
        Number of load bands

    Returns
    ----------
    MSLB: NumPy array
        Shares of capacity by tech x load band
    MLLB: NumPy array
        Load factors (%) by tech x load band
    MES1: NumPy array
        Upper market share limitation (1) -- virtually turned off
    MES2: NumPy array
        Lower market share limitation (2)


    Notes
    ---------
    None.

    """

    # dd is shorthand for load band suitability of different technologies
    dd = MWDD[0, :, :]

    # Technology logic identifiers
    s_not_var = 1.0 - dd[:, 5]

    # Convergence criterion
    crit = 0.0001

    # Initialize variables to return (for numba)
    MSLB = np.zeros((rti, t2ti, lbti))
    MLLB = np.zeros((rti, t2ti, lbti))
    MES1 = np.zeros((rti, t2ti, 1))
    MES2 = np.zeros((rti, t2ti, 1))

    for r in range(rti):

       
        p_tech = np.zeros((t2ti, lbti))
        p_grid = np.zeros((t2ti, lbti))
        #slb = np.zeros((t2ti, lbti))
        d_slb = np.zeros((t2ti, lbti))
        cflb = np.zeros((t2ti, lbti))
        q = 0
        d_s_tot = 1
        # Shares of capacity by tech
        s_i = s_not_var * MEWS[r, :, 0]
        # Shares of capacity by load band
        klb = np.zeros((lbti))
        klb[:5] = MKLB[r, :5, 0]
        # Average marginal cost
        m0 = np.sum(s_i * MWMC_lag[r, :, 0])
        
        # First, allocate nuclear to the baseload band
        if s_i[0] > 0.0:
            if klb[0] <= s_i[0]:
                MSLB[r,0,0] = MSLB[r,0,0] + klb[0]
                s_i[0] = s_i[0] - klb[0]
                klb[0] = 0.0
            else:
                klb[0] = klb[0] - s_i[0]
                MSLB[r,0,0] = MSLB[r,0,0] + s_i[0]
                s_i[0] = 0.0
                
            # Allocate any remaining nuclear to the next load band
            if klb[1] > 0.0 and s_i[0]>0.0:
                if klb[1]<= s_i[0]:
                    MSLB[r,0,1] = MSLB[r,0,1] + klb[1]
                    s_i[0] = s_i[0] - klb[1]
                    klb[1] = 0.0
                else:
                    klb[1] = klb[1] - s_i[0]
                    MSLB[r,0,1] = MSLB[r,0,1] + s_i[1]
                    s_i[0] = 0.0            
                

        # Technologies bid for generation time: weighted MNL
        # Constrained by size of load bands and available tech shares,
        # so allocate in an iterative process to try to find allocation closest
        # to preferences. Probabilistic 'college admissions'/'stable matching'
        while (s_i.sum() > crit and q < 50):

            for i in range(lbti - 1): # NOT intermittent renewables
                # TODO: In FORTRAN, MMC1 is chosen (which does not include negative carbon prices for BECCS). Switch either. 
                sig = np.sqrt(np.sum(dd[:,i] * MMCD_lag[r, :, 0]**2 * MEWS[r, :, 0]))
                exponent = -(MWMC_lag[r, :, 0] - m0) / sig
                fn = np.zeros((t2ti))
                # Approximate exponential
                fn[np.abs(exponent) < 20] = np.exp(exponent[np.abs(exponent) < 20])
                fn[exponent >= 20] = 1e9
                fn[exponent <= -20] = 1e-9
                
                # Multinomial logit or simplification
                if (np.sum(dd[:,i] * s_i) > 0 and sig > 0.001 and np.sum(dd[:,i] * s_i * fn) > 0):

                    p_tech[:, i] = dd[:,i]*s_i*fn / np.sum(dd[:,i]*s_i*fn)

                else:

                    p_tech[:, i] = np.zeros((t2ti))

            # Grid operator has preferences amongst what is bid for
            for k in range(t2ti):

                # p_grid is likelihood grid accepts bid from tech k
                sig = np.sqrt(np.sum(dd[k,:]*MMCD_lag[r, k, 0]**2))

                if (dd[k,5] == 0 and np.sum(dd[k,:]*klb) > 0 and sig > 0.001):

                    p_grid[k,:] = dd[k,:]*klb / np.sum(dd[k,:]*klb)

                else:

                    p_grid[k,:] = np.zeros((lbti))

            # Increment q
            q += 1
            # Allocate one round of generation to load bands according to p_grid, p_tech
            for i in range(lbti - 1):

                for k in range(t2ti):

                    d_slb[k, i] = np.abs(np.minimum(np.abs(s_i[k]), np.abs(klb[i])) * p_tech[k, i] * p_grid[k, i])

            d_slb[:, 5] = np.zeros((t2ti))
            # Cumulative allocations each round
            MSLB[r, :, :] = MSLB[r, :, :] + d_slb
            # Remove allocation from what's left per tech and load band
            s_i = s_i - np.sum(d_slb, axis=1)
            klb = klb - np.sum(d_slb, axis=0)
            d_s_tot = np.sum(d_slb)

        # Capacity of renewables
        for index in range(len(MWDD[0, :, 5])):
            if MWDD[0, index, 5]:
                MSLB[r, index, 5] = MEWS[r, index, 0]
        # slb[s_var, 5] = MEWS[r, s_var, 0]

        # Capacity factors by load band (definitionally)
        cflb[:, 0] = 7500 / 8766
        cflb[:, 1] = 4400 / 8766
        cflb[:, 2] = 2200 / 8766
        cflb[:, 3] = 700 / 8766
        cflb[:, 4] = 80 / 8766
        cflb[:, 5] = np.zeros((t2ti))
        
        for index in range(len(MWDD[0,:,5])):
            if MWDD[0,index,5]:
                cflb[index, 5] = MEWL[r, index, 0] # * (1 - MCRT[r,index,0])
        cflb = np.where(cflb==0, 1, cflb)
        # cflb[~cflb.astype(bool)] = 1

        # Save in data dict
#        MSLB[r,:,:] = slb*1
        MLLB[r,:,:] = cflb * 1

        # Upper share limit: set to ones for now (no upper limit, but
        # resistance to 100% market shares for any single tech)
        MES1[r, :, 0] = np.ones(t2ti)

        # Lower share limits
        # TODO: Are these compatible with storage cost incorporation? Maybe not...
        # Difference between availability (minus taken by other LB) and requirement per LB
        # Note this quantity is essentially what Gmin(i,j) takes tanh of
        grid_lim = np.zeros((5))

        grid_lim[4] = np.sum(dd[:, 4] * MEWS[r, :, 0]) - MKLB[r, 4, 0]
        grid_lim[3] = np.sum(dd[:, 3] * MEWS[r, :, 0]) - np.sum(MKLB[r, 3:5, 0])
        grid_lim[2] = np.sum(dd[:, 2] * MEWS[r, :, 0]) - np.sum(MKLB[r, 2:5, 0])
        grid_lim[1] = np.sum(dd[:, 1] * MEWS[r, :, 0]) - np.sum(MKLB[r, 1:5, 0])
        # No lower limit for baseload band
        grid_lim[0] = np.sum(dd[:, 0] * MEWS[r, :, 0]) - np.sum(MKLB[r, 0:5, 0])
        
        # Temp is shares minus grid_lim for suitable LB
        temp = np.zeros((t2ti, lbti))
        for i in range(1, lbti-1):
            temp[:,i] = dd[:,i] * (MEWS[r,:,0] - grid_lim[i])
        
        # For each tech, take largest value in temp or shares, whichever is less
        for i in range(t2ti):
            MES2[r, i, 0] = min(np.max(temp[i, :]), MEWS[r, i, 0])
            
        if r == 70:
            x = 1+1

    return MSLB, MLLB, MES1, MES2
