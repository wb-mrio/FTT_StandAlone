# -*- coding: utf-8 -*-
"""
=========================================
ftt_p_main.py
=========================================
Power generation FTT module.


This is the main file for the power module, FTT:Power. The power
module models technological replacement of electricity generation technologies due
to simulated investor decision making. Investors compare the **levelised cost of
electricity**, which leads to changes in the market shares of different technologies.

After market shares are determined, the rldc function is called, which calculates
**residual load duration curves**. This function estimates how much power needs to be
supplied by flexible or baseload technologies to meet electricity demand at all times.
This function also returns load band heights, curtailment, and storage information,
including storage costs and marginal costs for wind and solar.

FTT:Power also includes **dispatchers decisions**; dispatchers decide when different technologies
supply the power grid. Investor decisions and dispatcher decisions are matched up, which is an
example of a stable marraige problem.

Costs in the model change due to endogenous learning curves, costs for electricity
storage, as well as increasing marginal costs of resources calculated using cost-supply
curves. **Cost-supply curves** are recalculated at the end of the routine.

Local library imports:

    FTT: Power functions:

    - `rldc <ftt_p_rldc.html>`__
        Residual load duration curves
    - `dspch <ftt_p_dspch.html>`__
        Dispatch of capcity
    - `get_lcoe <ftt_p_lcoe.html>`__
        Levelised cost calculation
    - `survival_function <ftt_p_surv.html>`__
        Calculation of scrappage, sales, tracking of age, and average efficiency.
    - `shares <ftt_p_shares.html>`__
        Market shares simulation (core of the model)
    - `cost_curves <ftt_p_costc.html>`__
        Calculates increasing marginal costs of resources

    Support functions:

    - `divide <divide.html>`__
        Bespoke element-wise divide which replaces divide-by-zeros with zeros

Functions included:
    - solve
        Main solution function for the module
"""

# Standard library imports
from math import sqrt
import os
import copy
import sys
import warnings

# Third party imports
import pandas as pd
import numpy as np
from numba import njit

# Local library imports
from SourceCode.support.divide import divide
from SourceCode.Power.ftt_p_rldc import rldc
from SourceCode.Power.ftt_p_dspch import dspch
from SourceCode.Power.ftt_p_lcoe import get_lcoe
from SourceCode.Power.ftt_p_surv import survival_function
from SourceCode.Power.ftt_p_shares import shares
from SourceCode.Power.ftt_p_costc import cost_curves

# Local library imports for emulation
#from Emulation.code.ambition_vary import regional_ambition

# %% main function
# -----------------------------------------------------------------------------
# ----------------------------- Main ------------------------------------------
# -----------------------------------------------------------------------------
def solve(data, time_lag, iter_lag, titles, histend, year, domain):
    """
    Main solution function for the module.

    Add an extended description in the future.

    Parameters
    -----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution
    time_lag: type
        Description
    iter_lag: type
        Description
    titles: dictionary of lists
        Dictionary containing all title classification
    histend: dict of integers
        Final year of histrorical data by variable
    year: int
        Curernt/active year of solution
    Domain: dictionary of lists
        Pairs variables to domains

    Returns
    ----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution

    Notes
    ---------
    survival_function is currently unused.
    """
    # Categories for the cost matrix (BCET)
    c2ti = {category: index for index, category in enumerate(titles['C2TI'])}
    # jti = {category: index for index, category in enumerate(titles['JTI'])}

    # fuelvars = ['FR_1', 'FR_2', 'FR_3', 'FR_4', 'FR_5', 'FR_6',
    #             'FR_7', 'FR_8', 'FR_9', 'FR_10', 'FR_11', 'FR_12']


    # Conditional vectors concerning technology properties
    # (same for all regions, we use 1-USA)
    Svar = data['BCET'][:, :, c2ti['18 Variable (0 or 1)']]
    Sflex = data['BCET'][:, :, c2ti['19 Flexible (0 or 1)']]
    Sbase = data['BCET'][:, :, c2ti['20 Baseload (0 or 1)']]

    # TODO: THis is a generic survival function
    HalfLife = data['BCET'][:, :, c2ti['9 Lifetime (years)']]/2
    dLifeT = HalfLife/10

    for age in range(len(titles['TYTI'])):

        age_matrix = np.ones_like(data['MSRV'][:, :, age]) * age

        data['MSRV'][:, :, age] = 1.0 - 0.5*(1+np.tanh(1.25*(HalfLife-age_matrix)/dLifeT))

    # Store gamma values in the cost matrix (in case it varies over time)
    # TODO: Correct the title classification or delete?
    data['BCET'][:, :, c2ti['21 Empty']] = copy.deepcopy(data['MGAM'][:, :, 0])

    # Add in carbon costs due to EU ETS
    #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = copy.deepcopy(data['MCOCX'][:, :, 0])
    # attempting by switching r to : as not in region loop
    #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14] * (data['REPP'][r,0,0]/(data['PRSC'][r,0,0]/data['EX'][r,0,0])/(data['PRSC13'][r,0,0]/data['EX13'][r,0,0])*data['REX13'][33,0,0])/(1000*3.666)
    #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14]] * (data[“REPP”][:,0,0]/(data[“PRSC”][:,0,0]/data[“EX”][:,0,0])/(data[“PRSC13”][:,0,0]/data[“EX13”][:,0,0])*data[“REX13”][33,0,0])/(1000*3.666)
    data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14] * (data['REPP'][:,:,0]/(data['PRSC'][:,:,0]/data['EX'][:,:,0])/(data['PRSC13'][:,:,0]/data['EX13'][:,:,0])*data['REX13'][33,0,0])/(1000*3.666)
    
    
    
    
    # Copy over PRSC/EX values

    data['PRSC13'] = copy.deepcopy(time_lag['PRSC13'] )
    data['EX13'] = copy.deepcopy(time_lag['EX13'] )
    data['PRSC15'] = copy.deepcopy(time_lag['PRSC15'] )
    # %% First initialise if necessary

    T_Scal = 5      # Time scaling factor used in the share dynamics

    # Initialisation, which corresponds to lines 389 to 556 in fortran
    if year == 2013:
        data['PRSC13'] = copy.deepcopy(data['PRSCX'])
        data['EX13'] = copy.deepcopy(data['EXX'])

        data['MEWL'][:, :, 0] = data["MWLO"][:, :, 0]
        data['MEWK'][:, :, 0] = np.divide(data['MEWG'][:, :, 0], data['MEWL'][:, :, 0],
                              where=data['MEWL'][:, :, 0] > 0.0) / 8766
        data['MEWS'][:, :, 0] = np.divide(data['MEWK'][:,:,0], data['MEWK'][:,:,0].sum(axis=1)[:,np.newaxis],
                                          where=data['MEWK'][:, :, 0].sum(axis=1)[:,np.newaxis] > 0.0)

        bcet, bcsc, mewl, mepd, merc, rery, mred, mres = cost_curves(data['BCET'], time_lag['BCET'], data['MCSC'], data['MEWDX'], data['MEWG'], data['MEWL'], data['MEPD'],
                                                                     data['MERC'], time_lag['MERC'], data['RERY'], data['MPTR'], data['PMF'], data['MRED'], data['MRES'],
                                                                     titles['MTI'],titles['RTI'],titles['T2TI'],titles['C2TI'],titles['JTI'],
                                                                     titles['ERTI'],year,1.0,data['MERCX'])

        data['BCET'] = bcet
        data['MCSC'] = bcsc
        data['MEWL'] = mewl
        data['MEPD'] = mepd
        data['MERC'] = merc
        data['RERY'] = rery
        data['MRED'] = mred
        data['MRES'] = mres

        data = get_lcoe(data, titles)
        data = rldc(data, time_lag, titles)
        mslb, mllb, mes1, mes2 = dspch(data['MWDD'], data['MEWS'], data['MKLB'], data['MCRT'],
                                   data['MEWL'], data['MWMC'], data['MMCD'],
                                   len(titles['RTI']), len(titles['T2TI']), len(titles['LBTI']))
        data['MSLB'] = mslb
        data['MLLB'] = mllb
        data['MES1'] = mes1
        data['MES2'] = mes2
        # Total electricity demand
        tot_elec_dem = data['MEWDX'][:,7,0] * 1000/3.6

        earlysc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
        lifetsc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])

        for r in range(len(titles['RTI'])):

            # Generation by tech x load band is share of total electricity demand
            glb3 = data['MSLB'][r,:,:]*data['MLLB'][r,:,:]*tot_elec_dem[r]
            # Capacity by tech x load band
            klb3 = glb3/data['MLLB'][r,:,:]
            # Load factors

            data['MEWL'][r, :, 0] = np.zeros(len(titles['T2TI']))

            nonzero_cap = np.sum(klb3, axis=1)>0
            data['MEWL'][r, nonzero_cap, 0] = np.sum(glb3[nonzero_cap,:], axis=1)/np.sum(klb3[nonzero_cap,:], axis=1)

            # TODO: Remove once tested:
            #data['MEWL'] = copy.deepcopy(data['MEWLX'])


            # Generation by load band
            data['MWG1'][r, :, 0] = glb3[:, 0]
            data['MWG2'][r, :, 0] = glb3[:, 1]
            data['MWG3'][r, :, 0] = glb3[:, 2]
            data['MWG4'][r, :, 0] = glb3[:, 3]
            data['MWG5'][r, :, 0] = glb3[:, 4]
            data['MWG6'][r, :, 0] = glb3[:, 5]
            # To avoid division by 0 if 0 shares
            zero_lf = data['MEWL'][r,:,0]==0
            data['MEWL'][r, zero_lf, 0] = copy.deepcopy(data['MWLO'][r, zero_lf, 0])



            # Capacities
            data['MEWK'][r, :, 0] = divide(data['MEWG'][r, :, 0], data['MEWL'][r, :, 0]) / 8766

            # Investment (eq 8 Mercure EP48 2012)
#                data['MEWI'][r, :, 0] = (np.minimum(data['MEWK'][r, :, 0] - time_lag['MEWK'][r, :, 0], np.zeros(len(titles['T2TI']))) +
#                                         time_lag['MEWK'][r, :, 0] / time_lag['BCET'][r, :, c2ti['9 Lifetime (years)']])

            cap_diff = data['MEWK'][r, :, 0] - time_lag['MEWK'][r, :, 0]
            cap_drpctn = time_lag['MEWK'][r, :, 0] / time_lag['BCET'][r, :, c2ti['9 Lifetime (years)']]
            data['MEWI'][r, :, 0] = np.where(cap_diff > 0.0,
                                             cap_diff + cap_drpctn,
                                             cap_drpctn)
        data = get_lcoe(data, titles)


    #%%
    # Up to the last year of historical market share data
    if year <= histend['MEWG']:
        if year == 2015: data['PRSC15'] = copy.deepcopy(data['PRSCX'])


        # Set starting values for MERC
        data['MERC'][:, 0, 0] = 0.255
        data['MERC'][:, 1, 0] = 5.689
        data['MERC'][:, 2, 0] = 0.4246
        data['MERC'][:, 3, 0] = 3.374
        data['MERC'][:, 4, 0] = 0.001
        data['MERC'][:, 7, 0] = 0.001

        # Initialise load factors (last year's, or exogenous if first year)
#        loadfac = data['MEWLX'][:, :, 0]
#        if not loadfac.any():
#            loadfac = data['MWLO'][:, :, 0]
#        data['MEWL'][:, :, 0] = copy.deepcopy(loadfac)

        if year >2013: data['MEWL'][:, :, 0] = copy.deepcopy(time_lag['MEWL'][:, :, 0])

        cond=np.logical_and(data['MEWL'][:, :, 0] < 0.01, data['MWLO'][:, :, 0]>0.0)
        data['MEWL'][:, :, 0] = np.where(cond,
                                 data['MWLO'][:, :, 0],
                                 data['MEWL'][:, :, 0])


        # Initialise starting capacities
        if year <= 2012:
            data['MEWK'][:, :, 0] = np.divide(data['MEWG'][:, :, 0], data['MWLO'][:, :, 0],
                                          where=data['MWLO'][:, :, 0] > 0.0) / 8766
        else:
            data['MEWK'][:, :, 0] = np.divide(data['MEWG'][:, :, 0], data['MEWL'][:, :, 0],
                                          where=data['MEWL'][:, :, 0] > 0.0) / 8766

        #for r in range(len(titles['RTI'])):
        #    # Initialise starting market shares
        #    if np.sum(data['MEWK'][r, :, 0]) > 0.0:
        #        data['MEWS'][r, :, 0] = np.divide(data['MEWK'][r, :, 0],
        #                                          np.sum(data['MEWK'][r, :, 0]))
        data['MEWS'][:, :, 0] = np.divide(data['MEWK'][:,:,0], data['MEWK'][:,:,0].sum(axis=1)[:,np.newaxis],
                                          where=data['MEWK'][:, :, 0].sum(axis=1)[:,np.newaxis] > 0.0)

        # If first year, get initial MC, dMC for DSPCH
        if not time_lag['MMCD'][:, :, 0].any():
            time_lag = get_lcoe(data, titles)
        # Call RLDC function for capacity and load factor by LB, and storage costs
        if year >= 2013:
            print(f'MEWS: {data["MEWS"][40, 15, 0]:.7f}\n'
            f'MWSLt: {data["MEWS"][40, 15, 0]:.7f}\n' \
            f'MEWG: {data["MEWG"][40, 15, 0]:.0f}\n' \
            f'MEWK: {data["MEWK"][40, 15, 0]:.4f}\n' \
            f'MEWL: {data["MEWL"][40, 15, 0]:.7f}\n' \
            f'MWMC: {data["MWMC"][40, 2, 0]:.7f}\n' \
            f'MMCD: {data["MMCD"][40, 15, 0]:.5f}\n'\
            f'MKLB: {data["MKLB"][40, 0, 0]:.7f}\n' \
            f'MEWL: {data["MEWL"][40, 17, 0]:.5f}\n')

            # First, estimate marginal costs:
            #if year == 2013: data = get_lcoe(data, titles)

            # Second, estimate RLDC parameters
            bidon = 0
            data = rldc(data, time_lag, titles)

            # Change currency from EUR2015 to USD2013
            if year >= 2015:

                data['MSSP'][:, :, 0] = data['MSSP'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]
                data['MLSP'][:, :, 0] = data['MLSP'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]
                data['MSSM'][:, :, 0] = data['MSSM'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]
                data['MLSM'][:, :, 0] = data['MLSM'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]

            # TODO: This is not per se correct but it's how it is in E3ME
            else:

                data['MSSP'][:, :, 0] = 0.0
                data['MLSP'][:, :, 0] = 0.0
                data['MSSM'][:, :, 0] = 0.0
                data['MLSM'][:, :, 0] = 0.0

            # Third, call dispatch routine to connect market shares to load bands
            # Call DSPCH function to dispatch flexible capacity based on MC
            if year == 2013:
                mslb, mllb, mes1, mes2 = dspch(data['MWDD'], data['MEWS'], data['MKLB'], data['MCRT'],
                                        data['MEWL'], data['MWMC'], data['MMCD'],
                                        len(titles['RTI']), len(titles['T2TI']), len(titles['LBTI']))
            else:
                mslb, mllb, mes1, mes2 = dspch(data['MWDD'], data['MEWS'], data['MKLB'], data['MCRT'],
                                        data['MEWL'], time_lag['MWMC'], time_lag['MMCD'],
                                        len(titles['RTI']), len(titles['T2TI']), len(titles['LBTI']))
            data['MSLB'] = mslb
            data['MLLB'] = mllb
            data['MES1'] = mes1
            data['MES2'] = mes2

            # Total electricity demand
            tot_elec_dem = data['MEWDX'][:,7,0] * 1000/3.6

            earlysc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
            lifetsc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])

            for r in range(len(titles['RTI'])):

                # Generation by tech x load band is share of total electricity demand
                glb3 = data['MSLB'][r,:,:]*data['MLLB'][r,:,:]*tot_elec_dem[r]
                # Capacity by tech x load band
                klb3 = glb3/data['MLLB'][r,:,:]
                # Load factors

                data['MEWL'][r, :, 0] = np.zeros(len(titles['T2TI']))

                nonzero_cap = np.sum(klb3, axis=1)>0
                data['MEWL'][r, nonzero_cap, 0] = np.sum(glb3[nonzero_cap,:], axis=1)/np.sum(klb3[nonzero_cap,:], axis=1)

                # TODO: Remove once tested:
                #data['MEWL'] = copy.deepcopy(data['MEWLX'])


                # Generation by load band
                data['MWG1'][r, :, 0] = glb3[:, 0]
                data['MWG2'][r, :, 0] = glb3[:, 1]
                data['MWG3'][r, :, 0] = glb3[:, 2]
                data['MWG4'][r, :, 0] = glb3[:, 3]
                data['MWG5'][r, :, 0] = glb3[:, 4]
                data['MWG6'][r, :, 0] = glb3[:, 5]
                # To avoid division by 0 if 0 shares
                zero_lf = data['MEWL'][r,:,0]==0
                data['MEWL'][r, zero_lf, 0] = copy.deepcopy(data['MWLO'][r, zero_lf, 0])


                # C02 emissions for carbon costs (MtC02)
                data['MEWE'][r, :, 0] = data['MEWG'][r, :, 0]*data['BCET'][r, :, c2ti['15 Emissions (tCO2/GWh)']]/1e6

                # Capacities
                #data['MEWK'][r, :, 0] = divide(data['MEWG'][r, :, 0], data['MEWL'][r, :, 0]) / 8766

                # Investment (eq 8 Mercure EP48 2012)
#                data['MEWI'][r, :, 0] = (np.minimum(data['MEWK'][r, :, 0] - time_lag['MEWK'][r, :, 0], np.zeros(len(titles['T2TI']))) +
#                                         time_lag['MEWK'][r, :, 0] / time_lag['BCET'][r, :, c2ti['9 Lifetime (years)']])

                cap_diff = data['MEWK'][r, :, 0] - time_lag['MEWK'][r, :, 0]
                if year == 2013:    # FN: does starting MEWW contain 2013 values already? If so, count only depreciation, like Fortran code
                    cap_diff = data['MEWK'][r, :, 0] - data["MEWK"][r, :, 0]
                cap_drpctn = time_lag['MEWK'][r, :, 0] / time_lag['BCET'][r, :, c2ti['9 Lifetime (years)']]
                data['MEWI'][r, :, 0] = np.where(cap_diff > 0.0,
                                                 cap_diff + cap_drpctn,
                                                 cap_drpctn)


                # TODO: Clean this up - for now just an ugly loop
                for t in range(len(titles['T2TI'])):

                    if data['MEWK'][r, t, 0] - time_lag['MEWK'][r, t, 0] >= 0.0:

                        earlysc[r, t] = 0.0
                        lifetsc[r, t] = copy.deepcopy(time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']])
                        data['MESC'][r,t,0] = 0.0

                    else:

                        earlysc[r, t] = data['MEWK'][r, t, 0] - time_lag['MEWK'][r, t, 0]
                        lifetsc[r, t] = (1.0 - data['MEWK'][r, t, 0]/np.sum(data['MEWK'][r, :, 0])) * data['MEWK'][r, t, 0] / earlysc[r, t]*5

                    if (lifetsc[r, t]-time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']]) < 0.0:

                        data['MESC'][r,t,0] = -earlysc[r, t] * (
                                time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']] -
                                lifetsc[r, t]/data['BCET'][r, t, c2ti['9 Lifetime (years)']]*
                                time_lag['BCET'][r, t, c2ti['3 Investment ($/kW)']])

                        data['MELF'][r,t,0] = copy.deepcopy(lifetsc[r,t])

                    else:

                        data['MESC'][r,t,0] = 0.0
                        data['MELF'][r,t,0] = copy.deepcopy(time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']])



            # =============================================================
            # Learning-by-doing
            # =============================================================

            # Cumulative global learning
            # Using a technological spill-over matrix (MEWB) together with capacity
            # additions (MEWI) we can estimate total global spillover of similar
            # technologies
            bi = np.zeros((len(titles['RTI']),len(titles['T2TI'])))
            for r in range(len(titles['RTI'])):
                bi[r,:] = np.matmul(data['MEWB'][0, :, :],data['MEWI'][r, :, 0])
            dw = np.sum(bi, axis=0)

            # Cumulative capacity incl. learning spill-over effects
            data["MEWW"][0, :, 0] = time_lag['MEWW'][0, :, 0] + dw

            # Copy over the technology cost categories that do not change (all except prices which are updated through learning-by-doing below)
            data['BCET'][:, :, 1:17] = copy.deepcopy(time_lag['BCET'][:, :, 1:17])

            # Store gamma values in the cost matrix (in case it varies over time)
            # TODO: Correct the title classification or delete?
            data['BCET'][:, :, c2ti['21 Empty']] = copy.deepcopy(data['MGAM'][:, :, 0])

            # Add in carbon costs due to EU ETS
            #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = copy.deepcopy(data['MCOCX'][:, :, 0])
            data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14] * (data['REPP'][:,0,0]/(data['PRSC'][:,0,0]/data['EX'][:,0,0])/(data['PRSC13'][:,0,0]/data['EX13'][:,0,0])*data['REX13'][33,0,0])/(1000*3.666)

            
            
            # Learning-by-doing effects on investment
    #        for tech in range(len(titles['T2TI'])):
    #            if data['MEWW'][0, tech, 0] > 0.1:
    #                data['BCET'][:, tech, c2ti['3 Investment ($/kW)']] = time_lag['BCET'][:, tech, c2ti['3 Investment ($/kW)']] * \
    #                                                                       (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0])

            # Investment in terms of power technologies:
            for r in range(len(titles['RTI'])):
                data['MWIY'][r, :, 0] = time_lag['MWIY'][r, :, 0] + data['MEWI'][r, :, 0]*data['BCET'][r, :, c2ti['3 Investment ($/kW)']]/1.33

            # =====================================================================
            # Cost-supply curve
            # =====================================================================

            bcet, bcsc, mewl, mepd, merc, rery, mred, mres = cost_curves(data['BCET'], time_lag['BCET'], data['MCSC'], data['MEWDX'], data['MEWG'], data['MEWL'], data['MEPD'],
                                                                         data['MERC'], time_lag['MERC'], data['RERY'], data['MPTR'], data['PMF'], data['MRED'], data['MRES'],
                                                                         titles['MTI'],titles['RTI'],titles['T2TI'],titles['C2TI'],titles['JTI'],
                                                                         titles['ERTI'],year,1.0,data['MERCX'])

            data['BCET'] = bcet
            data['MCSC'] = bcsc
            data['MEWL'] = mewl
            data['MEPD'] = mepd
            data['MERC'] = merc
            data['RERY'] = rery
            data['MRED'] = mred
            data['MRES'] = mres


            # =====================================================================
            # Initialise the LCOE variables
            # =====================================================================
            data = get_lcoe(data, titles)
            bidon = 0
            # Historical differences between demand and supply.
            # This variable covers transmission losses and net exports
            # Hereafter, the lagged variable will have these values stored
            # We assume that the values do not change throughout simulation.
    #        data['MELO'][:, 0, 0] = data['MEWG'][:,:,0].sum(axis=1) - tot_elec_dem

# %% Simulation of stock and energy specs

    # Stock based solutions first
    elif year > histend['MEWG']:
        # TODO: Implement survival function to get a more accurate depiction of
        # technologies being phased out and to be able to track the age of the fleet.
        # This means that a new variable will need to be implemented which is
        # basically PG_VFLT with a third dimension (techicle age in years- up to 23y)
        # Reduced efficiences can then be tracked properly as well.

        # =====================================================================
        # Start of simulation
        # =====================================================================

        data_dt = {}

        # First, fill the time loop variables with the their lagged equivalents
        for var in time_lag.keys():

            if domain[var] == 'FTT-P':

                data_dt[var] = copy.deepcopy(time_lag[var])

        data_dt['MWIY'] = np.zeros([len(titles['RTI']), len(titles['T2TI']), 1])

        # Create new regulation variable for emulation
        isReg = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
        isReg = data['MEWR'][:, :, 0]

        # Create the regulation variable (previous)
        isReg = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
        division = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
        division = np.divide((data_dt['MEWK'][:, :, 0] - data['MEWR'][:, :, 0]),
                             data['MEWR'][:, :, 0],
                             where=data['MEWR'][:, :, 0] > 0.0)
        try:
            isReg = 1 + np.tanh(2*1.25*division)
        except RuntimeWarning:
            print('stop')
            isReg = 1 + np.tanh(2*1.25*division)

        isReg[data['MEWR'][:, :, 0] == 0.0] = 1.0
        isReg[data['MEWR'][:, :, 0] == -1.0] = 0.0



        # Call the survival function routine.
#        data = survival_function(data, time_lag, histend, year, titles)

        # Total number of scrapped techicles:
#        tot_eol = np.sum(data['MEOL'][:, :, 0], axis=1)

        # Total capacity additions
#        data['MWIA'][:, 0, 0] = (data['PG_TTC'][:, 0, 0]
#                                   - time_lag['PG_TTC'][:, 0, 0]
#                                   + tot_eol)
#        data['MWIA'][:, 0, 0][data['MEWKA'][:, 0, 0] < 0.0] = 0.0

        # Factor used to create quarterly data from annual figures
        no_it = 4
        dt = 1 / no_it

        # store exogenous load factors in local variable
        loadfac = copy.deepcopy(data['MWLO'][:, :, 0])

        # =====================================================================
        # Start of the quarterly time-loop
        # =====================================================================

        #Start the computation of shares
        for t in range(1, no_it+1):

            # Electricity demand is exogenous at the moment
            # TODO: Replace, using price elasticities and feedback from other
            # FTT modules
            lag_demand = time_lag['MEWDX'][:, 7, 0] * 1000/3.6

            e_demand = (lag_demand + (data['MEWDX'][:,7,0] * 1000/3.6 - lag_demand) * t * dt)

            e_demand_step = ((data['MEWDX'][:,7,0] * 1000/3.6 - lag_demand) * dt)

            # =================================================================
            # Share equation
            # =================================================================
            bidon = 0
            #
            mews, mewl, mewg, mewk = shares(dt, T_Scal, e_demand, e_demand_step,
                                            data_dt['MEWS'], data_dt['METC'],
                                            data_dt['MTCD'], data['MWKA'],
                                            data_dt['MES1'], data_dt['MES2'],
                                            data['MEWA'], isReg, data_dt['MEWK'],
                                            data_dt['MEWK'], data['MEWR'],
                                            data_dt['MEWL'], data_dt['MEWS'],
                                            data['MWLO'], lag_demand,
                                            len(titles['RTI']), len(titles['T2TI']))
            data['MEWS'] = mews
            data['MEWL'] = mewl
            data['MEWG'] = mewg
            data['MEWK'] = mewk
            bidon = 0

            # =================================================================
            # Residual load-duration curve
            # =================================================================
            # Call RLDC function for capacity and load factor by LB, and storage costs
            data = rldc(data, time_lag, titles)
            bidon = 0
            # Change currency from EUR2015 to USD2013

            if year >= 2015:

                data['MSSP'][:, :, 0] = data['MSSP'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]
                data['MLSP'][:, :, 0] = data['MLSP'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]
                data['MSSM'][:, :, 0] = data['MSSM'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]
                data['MLSM'][:, :, 0] = data['MLSM'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis])/ data['EX13'][33, 0, 0]

            # TODO: This is not per se correct but it's how it is in E3ME
            else:

                data['MSSP'][:, :, 0] = 0.0
                data['MLSP'][:, :, 0] = 0.0
                data['MSSM'][:, :, 0] = 0.0
                data['MLSM'][:, :, 0] = 0.0

            # =================================================================
            # Dispatch routine
            # =================================================================
            # Call DSPCH function to dispatch flexible capacity based on MC
            # data = dspch(data, time_lag, titles)

            mslb, mllb, mes1, mes2 = dspch(data['MWDD'], data['MEWS'], data['MKLB'], data['MCRT'],
                                           data['MEWL'], data_dt['MWMC'], data_dt['MMCD'],
                                           len(titles['RTI']), len(titles['T2TI']), len(titles['LBTI']))
            data['MSLB'] = mslb
            data['MLLB'] = mllb
            data['MES1'] = mes1
            data['MES2'] = mes2

            # Total electricity demand
            tot_elec_dem = data['MEWDX'][:,7,0] * 1000/3.6

            for r in range(len(titles['RTI'])):
                # Generation by tech x load band is share of total electricity demand
                glb3 = data['MSLB'][r,:,:]*data['MLLB'][r,:,:]*tot_elec_dem[r]
                # Capacity by tech x load band
                klb3 = glb3/data['MLLB'][r,:,:]
                # Load factors
                data['MEWL'][r, :, 0] = np.zeros(len(titles['T2TI']))
                nonzero_cap = np.sum(klb3, axis=1)>0
                data['MEWL'][r, nonzero_cap, 0] = np.sum(glb3[nonzero_cap,:], axis=1)/np.sum(klb3[nonzero_cap,:], axis=1)
                # Generation by load band
                data['MWG1'][r, :, 0] = glb3[:, 0]
                data['MWG2'][r, :, 0] = glb3[:, 1]
                data['MWG3'][r, :, 0] = glb3[:, 2]
                data['MWG4'][r, :, 0] = glb3[:, 3]
                data['MWG5'][r, :, 0] = glb3[:, 4]
                data['MWG6'][r, :, 0] = glb3[:, 5]
                # To avoid division by 0 if 0 shares
                zero_lf = data['MEWL'][r,:,0]==0
                data['MEWL'][r, zero_lf, 0] = data["MWLO"][r, zero_lf, 0]

                # Re-calculate capacities
#                data['MEWK'][r, :, 0] = divide(data['MEWG'][r, :, 0], data['MEWL'][r, :, 0])/8766

            # =============================================================
            #  Update variables
            # =============================================================

            # Adjust capacity factors for VRE due to curtailment and storage efficiency losses
            data['MCRG'][:, 0, 0] = data['MCRT'][:, 0, 0]*e_demand
            data['MADG'][:, 0, 0] = data['MCRG'][:, 0, 0] + data['MSSG'][:, 0, 0] + data['MLSG'][:, 0, 0]
            mewg_int = data['MEWS'][:, :, 0]*e_demand[:, np.newaxis]*data['MEWL'][:, :, 0]/np.sum(data['MEWS'][:, :, 0]*data['MEWL'][:, :, 0], axis=1)[:, np.newaxis]
            mewg_add = np.zeros_like(mewg_int)
            mewg_add = np.divide(mewg_int*Svar[:, :], np.sum(mewg_int*Svar[:, :], axis=1)[:, np.newaxis], where=(np.sum(mewg_int*Svar[:, :], axis=1)[:, np.newaxis] > 0))
            # Update generation
            denominator = np.sum(data['MEWS'][:, :, 0]*data['MEWL'][:, :, 0], axis=1)[:, np.newaxis]
            data['MEWG'][:, :, 0] = np.zeros((len(titles['RTI']), len(titles['T2TI'])))
            data['MEWG'][:, :, 0] = np.divide(data['MEWS'][:, :, 0] * e_demand[:, np.newaxis] * data['MEWL'][:, :, 0],
                                              denominator,
                                              where=denominator > 0.0) + mewg_add*data['MADG'][:, 0, 0, np.newaxis]

            # Just for testing:
#            data['MEWG'][:, :, 0] = copy.deepcopy(data['MEWGX'][:, :, 0])
#            data['MEWL'][:, :, 0] = copy.deepcopy(data['MEWLX'][:, :, 0])


            # Update capacities
            data['MEWK']= divide(data['MEWG'], data['MEWL']) / 8766
            # Update emissions
            data['MEWE'][:, :, 0] = data['MEWG'][:, :, 0] * data['BCET'][:, :, c2ti['15 Emissions (tCO2/GWh)']] / 1e6
            # Investment (eq 8 Mercure EP48 2012)
#            data['MEWI'][:, :, 0] = (np.minimum(data['MEWK'][:, :, 0] - data_dt['MEWK'][:, :, 0], np.zeros((len(titles['RTI']), len(titles['T2TI'])))) +
#                                     data_dt['MEWK'][:, :, 0] / data['BCET'][:, :, c2ti['9 Lifetime (years)']])

            #cap_diff = data['MEWK'][:, :, 0] - time_lag['MEWK'][:, :, 0]
            #cap_drpctn = time_lag['MEWK'][:, :, 0] / time_lag['BCET'][:, :, c2ti['9 Lifetime (years)']]
            cap_diff = (data['MEWK'][:, :, 0] - data_dt['MEWK'][:, :, 0])/dt
            cap_dprctn = data_dt['MEWK'][:, :, 0] / time_lag['BCET'][:, :, c2ti['9 Lifetime (years)']]
            data['MEWI'][:, :, 0] = np.where(cap_diff > 0.0,
                                             cap_diff + cap_dprctn,
                                             cap_dprctn)

            earlysc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
            lifetsc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])

            for r in range(len(titles['RTI'])):
            # TODO: Clean this up - for now just an ugly loop
                for tech in range(len(titles['T2TI'])):

                    if data['MEWK'][r, tech, 0] - data_dt['MEWK'][r, tech, 0] >= 0.0:

                        earlysc[r, tech] = 0.0
                        lifetsc[r, tech] = copy.deepcopy(data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']])
                        data['MESC'][r,tech,0] = 0.0

                    else:

                        earlysc[r, tech] = data['MEWK'][r, tech, 0] - data_dt['MEWK'][r, tech, 0]
                        lifetsc[r, tech] = (1.0 - data['MEWK'][r, tech, 0]/np.sum(data['MEWK'][r, :, 0])) * (data['MEWK'][r, tech, 0] / earlysc[r, tech]) * 5

                    if (lifetsc[r, tech]-data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']]) < 0.0:

                        data['MESC'][r,tech,0] = -earlysc[r, tech] * (
                                (data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']] - lifetsc[r, tech]) /
                                data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']] *
                                data_dt['BCET'][r, tech, c2ti['3 Investment ($/kW)']])

                        data['MELF'][r,tech,0] = copy.deepcopy(lifetsc[r,tech])

                    else:

                        data['MESC'][r,tech,0] = 0.0
                        data['MELF'][r,tech,0] = copy.deepcopy(data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']])

            # =============================================================
            # Learning-by-doing
            # =============================================================

            # Cumulative global learning
            # Using a technological spill-over matrix (PG_SPILL) together with capacity
            # additions (PG_CA) we can estimate total global spillover of similar
            # techicals
#            bi = np.matmul(data['MEWI'][:, :, 0], data['MEWB'][0, :, :])
#            dw = np.sum(bi, axis=0)

            bi = np.zeros((len(titles['RTI']),len(titles['T2TI'])))
            for r in range(len(titles['RTI'])):
                bi[r,:] = np.matmul(data['MEWB'][0, :, :],data['MEWI'][r, :, 0])
            dw = np.sum(bi, axis=0)

            # Cumulative capacity incl. learning spill-over effects
            data["MEWW"][0, :, 0] = data_dt['MEWW'][0, :, 0] + dw

            # Copy over the technology cost categories that do not change (all except prices which are updated through learning-by-doing below)
            data['BCET'][:, :, 1:17] = copy.deepcopy(time_lag['BCET'][:, :, 1:17])

            # Store gamma values in the cost matrix (in case it varies over time)
            # TODO: Correct the title classification or delete?
            data['BCET'][:, :, c2ti['21 Empty']] = copy.deepcopy(data['MGAM'][:, :, 0])

            # Add in carbon costs due to EU ETS
            #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = copy.deepcopy(data['MCOCX'][:, :, 0])

            data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14] * (data['REPP'][:,0,0]/(data['PRSC'][:,0,0]/data['EX'][:,0,0])/(data['PRSC13'][:,0,0]/data['EX13'][:,0,0])*data['REX13'][33,0,0])/(1000*3.666)

            
            # Learning-by-doing effects on investment
            for tech in range(len(titles['T2TI'])):

                if data['MEWW'][0, tech, 0] > 0.1:

                    data['BCET'][:, tech, c2ti['3 Investment ($/kW)']] = data_dt['BCET'][:, tech, c2ti['3 Investment ($/kW)']] * \
                                                                           (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0])
                    data['BCET'][:, tech, c2ti['4 std ($/MWh)']] = data_dt['BCET'][:, tech, c2ti['4 std ($/MWh)']] * \
                                                                          (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0])

            # Investment in power sector technologies
            for r in range(len(titles['RTI'])):

                data['MWIY'][r, :, 0] = data_dt['MWIY'][r, :, 0] + data['MEWI'][r, :, 0]*dt*data['BCET'][r, :, c2ti['3 Investment ($/kW)']]/1.33

            # =================================================================
            # Cost-supply curves
            # =================================================================
            if t == no_it:
               #                print("Did we pass this point?")
                bcet, bcsc, mewl, mepd, merc, rery, mred, mres = cost_curves(data['BCET'], data_dt['BCET'], data['MCSC'], data['MEWDX'], data['MEWG'], data['MEWL'], data['MEPD'],
                                                                             data['MERC'], time_lag['MERC'], data['RERY'], data['MPTR'], data['PMF'], data['MRED'], data['MRES'],
                                                                             titles['MTI'],titles['RTI'],titles['T2TI'],titles['C2TI'],titles['JTI'],
                                                                             titles['ERTI'],year,1.0,data['MERCX'])

                data['BCET'] = bcet
                data['MCSC'] = bcsc
                data['MEWL'] = mewl
                data['MEPD'] = mepd
                data['MERC'] = merc
                data['RERY'] = rery
                data['MRED'] = mred
                data['MRES'] = mres

            # =================================================================
            # Update LCOE
            # =================================================================

            data = get_lcoe(data, titles)

            # =================================================================
            # Update the time-loop variables
            # =================================================================

            # Update time loop variables:
            
            print(year)
            print(f'MEWS: {data["MEWS"][40, 16, 0]:.7f}\n'
             f'MWSLt: {data_dt["MEWS"][40, 16, 0]:.7f}\n' \
             f'MEWG: {data["MEWG"][40, 16, 0]:.0f}\n' \
             f'MEWK: {data["MEWK"][40, 16, 0]:.4f}\n' \
             f'MEWL: {data["MEWL"][40, 16, 0]:.7f}\n' \
             f'METC: {data["METC"][40, 16, 0]:.7f}\n'\
             f'MWMC: {data_dt["MWMC"][40, 2, 0]:.7f}\n' \
             f'MMCD: {data_dt["MMCD"][40, 16, 0]:.5f}\n')
            for var in data_dt.keys():

                if domain[var] == 'FTT-P':

                    data_dt[var] = copy.deepcopy(data[var])


    return data
