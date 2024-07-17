# -*- coding: utf-8 -*-
"""
=========================================
ftt_p_main.py
=========================================
Power generation FTT module.


This is the main file for the power module, FTT: Power. The power
module models technological replacement of electricity generation technologies due
to simulated investor decision making. Investors compare the **levelised cost of
electricity**, which leads to changes in the market shares of different technologies.

After market shares are determined, the rldc function is called, which calculates
**residual load duration curves**. This function estimates how much power needs to be
supplied by flexible or baseload technologies to meet electricity demand at all times.
This function also returns load band heights, curtailment, and storage information,
including storage costs and marginal costs for wind and solar.

FTT: Power also includes **dispatchers decisions**; dispatchers decide when different technologies
supply the power grid. Investor decisions and dispatcher decisions are matched up, which is an
example of a stable marraige problem.

Costs in the model change due to endogenous learning curves, costs for electricity
storage, as well as increasing marginal costs of resources calculated using cost-supply
curves. **Cost-supply curves** are recalculated at the end of the routine.

Local library imports:

    FTT: Core functions:
    - `get_sales <get_sales_or_investment.htlm>
        Generic investment function (new plus end-of-life replacement)
        
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

# Third party imports
import numpy as np

# Local library imports
from SourceCode.support.divide import divide
from SourceCode.ftt_core.ftt_sales_or_investments import get_sales, get_sales_yearly
from SourceCode.Power.ftt_p_rldc import rldc
from SourceCode.Power.ftt_p_dspch import dspch
from SourceCode.Power.ftt_p_lcoe import get_lcoe
from SourceCode.Power.ftt_p_surv import survival_function
from SourceCode.Power.ftt_p_shares import shares
from SourceCode.Power.ftt_p_costc import cost_curves



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
        Model variables for the current year
    time_lag: type
        Model variables in previous year
    iter_lag: type
        Description
    titles: dictionary of lists
        Dictionary containing all title classification
    histend: dict of integers
        Final year of historical data by variable
    year: int
        Current/active year of solution
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


    # Conditional vector concerning technology properties
    # (same for all regions)
    Svar = data['BCET'][:, :, c2ti['18 Variable (0 or 1)']]


    # TODO: This is a generic survival function
    HalfLife = data['BCET'][:, :, c2ti['9 Lifetime (years)']]/2
    dLifeT = HalfLife/10

    for age in range(len(titles['TYTI'])):

        age_matrix = np.ones_like(data['MSRV'][:, :, age]) * age

        data['MSRV'][:, :, age] = 1.0 - 0.5*(1+np.tanh(1.25*(HalfLife-age_matrix)/dLifeT))

    # Store gamma values in the cost matrix (in case it varies over time)
    data['BCET'][:, :, c2ti['21 Gamma ($/MWh)']] = data['MGAM'][:, :, 0]

    # Add in carbon costs due to EU ETS
    #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = copy.deepcopy(data['MCOCX'][:, :, 0])
    # create variable to apply to carbon costs then convert shape to match BCET
    convert_cp = (data['REPP'][:,0,0]/(data['PRSC'][:,0,0]/data['EX'][:,0,0])/(data['PRSC13'][:,0,0]/data['EX13'][:,0,0])*data['REX13'][33,0,0])/(1000*3.666)
    data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14] * convert_cp[:, np.newaxis]

    # Copy over PRSC/EX values

    data['PRSC13'] = np.copy(time_lag['PRSC13'] )
    data['EX13'] = np.copy(time_lag['EX13'] )
    data['PRSC15'] = np.copy(time_lag['PRSC15'] )
    # %% First initialise if necessary

    T_Scal = 10      # Time scaling factor used in the share dynamics

    # Initialisation, which corresponds to lines 389 to 556 in fortran
    # Changing from PRSCX to PRSC for emulation and CP calculation
    if year == 2013:
        #data['PRSC13'] = copy.deepcopy(data['PRSCX'])
        #data['EX13'] = copy.deepcopy(data['EXX'])
        data['PRSC13'] = copy.deepcopy(data['PRSC'])
        data['EX13'] = copy.deepcopy(data['EX'])


        data['MEWL'][:, :, 0] = data["MWLO"][:, :, 0]
        data['MEWK'][:, :, 0] = np.divide(data['MEWG'][:, :, 0], data['MEWL'][:, :, 0],
                              where=data['MEWL'][:, :, 0] > 0.0) / 8766
        data['MEWS'][:, :, 0] = np.divide(data['MEWK'][:,:,0], data['MEWK'][:,:,0].sum(axis=1)[:,np.newaxis],
                                          where=data['MEWK'][:, :, 0].sum(axis=1)[:,np.newaxis] > 0.0)

        bcet, bcsc, mewl, mepd, merc, rery, mred, mres = cost_curves(
                data['BCET'], data['MCSC'], data['MEWDX'], data['MEWG'], data['MEWL'], data['MEPD'],
                data['MERC'], time_lag['MERC'], data['RERY'], data['MPTR'], data['MRED'], data['MRES'],
                titles['RTI'], titles['T2TI'], titles['ERTI'], year, 1.0
                )

        data['BCET'] = bcet
        data['MCSC'] = bcsc
        data['MEWL'] = mewl
        data['MEPD'] = mepd
        data['MERC'] = merc
        data['RERY'] = rery
        data['MRED'] = mred
        data['MRES'] = mres

        data = get_lcoe(data, titles)
        data = rldc(data, time_lag, iter_lag, year, titles)
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
            glb3 = data['MSLB'][r,:,:] * data['MLLB'][r,:,:] * tot_elec_dem[r]
            # Capacity by tech x load band
            klb3 = glb3 / data['MLLB'][r,:,:]
            
            # Load factors
            data['MEWL'][r, :, 0] = np.zeros(len(titles['T2TI']))

            nonzero_cap = np.sum(klb3, axis=1)>0
            data['MEWL'][r, nonzero_cap, 0] =  np.sum(glb3[nonzero_cap, :], axis=1) / np.sum(klb3[nonzero_cap,:], axis=1)
                                                            

            # Generation by load band
            data['MWG1'][r, :, 0] = glb3[:, 0]
            data['MWG2'][r, :, 0] = glb3[:, 1]
            data['MWG3'][r, :, 0] = glb3[:, 2]
            data['MWG4'][r, :, 0] = glb3[:, 3]
            data['MWG5'][r, :, 0] = glb3[:, 4]
            data['MWG6'][r, :, 0] = glb3[:, 5]
            # To avoid division by 0 if 0 shares
            zero_lf = data['MEWL'][r,:,0]==0
            data['MEWL'][r, zero_lf, 0] = data['MWLO'][r, zero_lf, 0]
            
            

            # Capacities
            data['MEWK'][r, :, 0] = divide(data['MEWG'][r, :, 0], data['MEWL'][r, :, 0]) / 8766
            
            # Update market shares
            data["MEWS"][r, :, 0] = data['MEWK'][r, :, 0] / data['MEWK'][r, :, 0].sum()
            
            
            cap_diff = data['MEWK'][r, :, 0] - time_lag['MEWK'][r, :, 0]
            cap_drpctn = time_lag['MEWK'][r, :, 0] / time_lag['BCET'][r, :, c2ti['9 Lifetime (years)']]
            data['MEWI'][r, :, 0] = np.where(cap_diff > 0.0,
                                             cap_diff + cap_drpctn,
                                             cap_drpctn)
            

       
        data['MEWL'][:, :, 0] = data['MWLO'][:, :, 0].copy()
        data['MCFC'][:, :, 0] = data['MWLO'][:, :, 0].copy()
        data['BCET'][:, :, c2ti['11 Decision Load Factor']] = data['MCFC'][:, :, 0].copy()
        
        data = get_lcoe(data, titles)


    #%%
    # Up to the last year of historical market share data
    elif year <= histend['MEWG']:
        if year == 2015: 
            data['PRSC15'] = np.copy(data['PRSCX'])


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
#        data['MEWL'][:, :, 0] = np.copy(loadfac)

        if year > 2013: 
            data['MEWL'][:, :, 0] = time_lag['MEWL'][:, :, 0].copy()

        cond = np.logical_and(data['MEWL'][:, :, 0] < 0.01, data['MWLO'][:, :, 0] > 0.0)
        data['MEWL'][:, :, 0] = np.where(cond,
                                 data['MWLO'][:, :, 0],
                                 data['MEWL'][:, :, 0])


        # Initialise starting capacities
        if year <= 2012:
            data['MEWK'][:, :, 0] = divide(data['MEWG'][:, :, 0], data['MWLO'][:, :, 0]) / 8766
        else:
            data['MEWK'][:, :, 0] = divide(data['MEWG'][:, :, 0], data['MEWL'][:, :, 0]) / 8766

        data['MEWS'][:, :, 0] = np.divide(data['MEWK'][:,:,0], data['MEWK'][:,:,0].sum(axis=1)[:,np.newaxis])

        # If first year, get initial MC, dMC for DSPCH ( TODO FORTRAN??)
        if not time_lag['MMCD'][:, :, 0].any():
            time_lag = get_lcoe(data, titles)
        # Call RLDC function for capacity and load factor by LB, and storage costs
        if year >= 2013:

            # 1 and 2 -- Estimate RLDC and storage parameters
            data = rldc(data, time_lag, iter_lag, year, titles)

            # 3--- Call dispatch routine to connect market shares to load bands
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

            # Total electricity demand
            tot_elec_dem = data['MEWDX'][:, 7, 0] * 1000/3.6

            earlysc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
            lifetsc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
            
            # 4--- Calculate average capacity factors according to load bands
            for r in range(len(titles['RTI'])):

                # Generation by tech x load band is share of total electricity demand
                glb3 = data['MSLB'][r,:,:] * data['MLLB'][r,:,:] * tot_elec_dem[r]
                # Capacity by tech x load band
                klb3 = glb3/data['MLLB'][r, :, :]
                # Load factors

                data['MEWL'][r, :, 0] = np.zeros(len(titles['T2TI']))

                nonzero_cap = np.sum(klb3, axis=1)>0
                data['MEWL'][r, nonzero_cap, 0] = np.sum(glb3[nonzero_cap,:], axis=1) / np.sum(klb3[nonzero_cap,:], axis=1)


                # Generation by load band
                data['MWG1'][r, :, 0] = glb3[:, 0]
                data['MWG2'][r, :, 0] = glb3[:, 1]
                data['MWG3'][r, :, 0] = glb3[:, 2]
                data['MWG4'][r, :, 0] = glb3[:, 3]
                data['MWG5'][r, :, 0] = glb3[:, 4]
                data['MWG6'][r, :, 0] = glb3[:, 5]
                # To avoid division by 0 if 0 shares
                zero_lf = data['MEWL'][r, :, 0] == 0
                data['MEWL'][r, zero_lf, 0] = data['MWLO'][r, zero_lf, 0]
                
                # Adjust capacity factors for VRE due to curtailment, and to cover efficiency losses during
                # Gross Curtailed electricity
                data['MCGA'][r, 0, 0] = data['MCRT'][r,0,0] * np.sum(Svar[r, :] * data['MEWG'][r,:,0])

                # Net curtailed generation
                # Remove long-term storage demand and assume that at least 45% of gross curtailment is retained.
                # On average 45% of curtailed electricity can be reused for long-term storage:
                # Source: https://www.frontiersin.org/articles/10.3389/fenrg.2020.527910/full
                data['MCNA'][r, 0, 0] = np.maximum(data['MCGA'][r, 0, 0] - 0.45*2*data['MLSG'][r,0,0], 0.55*data['MCGA'][r,0,0])
                # Impact of net curtailment on load factors for VRE technologies
                # Scale down the curtailment rate by taking into account the electricity that is actually used for long-term storage
                data['MCTN'][r, :, 0] = data['MCTG'][r, :, 0] * data['MCNA'][r, 0, 0] / data['MCGA'][r, 0, 0]
                                
                # Total additional electricity that needs to be generated
                data['MADG'][r,0,0] = data['MCGA'][r,0,0] - data['MCNA'][r, 0, 0] + data['MSSG'][r,0,0]
                
                data['MEWK'][:, :, 0] = divide(data['MEWG'][:, :, 0], data['MEWL'][:, :, 0]) / 8766
                
                data['MEWS'][:, :, 0] = np.divide(data['MEWK'][:,:,0], data['MEWK'][:,:,0].sum(axis=1)[:,np.newaxis],
                                                  where=data['MEWK'][:, :, 0].sum(axis=1)[:,np.newaxis] > 0.0)

                # C02 emissions for carbon costs (MtC02)
                data['MEWE'][r, :, 0] = data['MEWG'][r, :, 0] * data['BCET'][r, :, c2ti['15 Emissions (tCO2/GWh)']]/1e6

                # Capacities
                #data['MEWK'][r, :, 0] = divide(data['MEWG'][r, :, 0], data['MEWL'][r, :, 0]) / 8766

                # Investment (eq 8 Mercure EP48 2012)
#                data['MEWI'][r, :, 0] = (np.minimum(data['MEWK'][r, :, 0] - time_lag['MEWK'][r, :, 0], np.zeros(len(titles['T2TI']))) +
#                                         time_lag['MEWK'][r, :, 0] / time_lag['BCET'][r, :, c2ti['9 Lifetime (years)']])

                cap_diff = data['MEWK'][r, :, 0] - time_lag['MEWK'][r, :, 0]
                cap_drpctn = time_lag['MEWK'][r, :, 0] / time_lag['BCET'][r, :, c2ti['9 Lifetime (years)']]
                data['MEWI'][r, :, 0] = np.where(cap_diff > 0.0,
                                                 cap_diff + cap_drpctn,
                                                 cap_drpctn)


                # TODO: Clean this up - for now just an ugly loop
                for t in range(len(titles['T2TI'])):

                    if data['MEWK'][r, t, 0] - time_lag['MEWK'][r, t, 0] >= 0.0:

                        earlysc[r, t] = 0.0
                        lifetsc[r, t] = time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']]
                        data['MESC'][r,t,0] = 0.0

                    else:

                        earlysc[r, t] = data['MEWK'][r, t, 0] - time_lag['MEWK'][r, t, 0]
                        lifetsc[r, t] = (1.0 - data['MEWK'][r, t, 0]/np.sum(data['MEWK'][r, :, 0])) * data['MEWK'][r, t, 0] / earlysc[r, t]*5

                    if (lifetsc[r, t]-time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']]) < 0.0:

                        data['MESC'][r,t,0] = -earlysc[r, t] * (
                                time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']] -
                                lifetsc[r, t]/data['BCET'][r, t, c2ti['9 Lifetime (years)']]*
                                time_lag['BCET'][r, t, c2ti['3 Investment ($/kW)']])

                        data['MELF'][r,t,0] = lifetsc[r, t]

                    else:

                        data['MESC'][r,t,0] = 0.0
                        data['MELF'][r,t,0] = time_lag['BCET'][r, t, c2ti['9 Lifetime (years)']]



            # =============================================================
            # Learning-by-doing
            # =============================================================

            # Cumulative global learning
            # Using a technological spill-over matrix (MEWB) together with capacity
            # additions (MEWI) we can estimate total global spillover of similar techs

            mewi0 = np.sum(data['MEWI'][:, :, 0], axis=0)
            dw = np.zeros(len(titles["T2TI"]))
            
            for i in range(len(titles["T2TI"])):
                dw_temp = np.copy(mewi0)
                dw_temp[dw_temp > dw_temp[i]] = dw_temp[i]
                dw[i] = np.dot(dw_temp, data['MEWB'][0, i, :])

            # Cumulative capacity incl. learning spill-over effects
            data["MEWW"][0, :, 0] = time_lag['MEWW'][0, :, 0] + dw

            # Copy over the technology cost categories that do not change (all except prices which are updated through learning-by-doing below)
            data['BCET'][:, :, 1:17] = time_lag['BCET'][:, :, 1:17].copy()

            # Store gamma values in the cost matrix (in case it varies over time)
            data['BCET'][:, :, c2ti['21 Gamma ($/MWh)']] = data['MGAM'][:, :, 0]

            # Add in carbon costs due to EU ETS
            #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = copy.deepcopy(data['MCOCX'][:, :, 0])
            convert_cp = (data['REPP'][:,0,0]/(data['PRSC'][:,0,0]/data['EX'][:,0,0])/(data['PRSC13'][:,0,0]/data['EX13'][:,0,0])*data['REX13'][33,0,0])/(1000*3.666)
            data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14] * convert_cp[:, np.newaxis]


            # Learning-by-doing effects on investment
            if year > histend['BCET']:
                for tech in range(len(titles['T2TI'])):
                    if data['MEWW'][0, tech, 0] > 0.1:
                        data['BCET'][:, tech, c2ti['3 Investment ($/kW)']] = time_lag['BCET'][:, tech, c2ti['3 Investment ($/kW)']] * \
                                                                                (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0])
                        data['BCET'][:, tech, c2ti['4 std ($/MWh)']] = time_lag['BCET'][:, tech, c2ti['4 std ($/MWh)']] * \
                                                                            (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0])
                        data['BCET'][:, tech, c2ti['7 O&M ($/MWh)']] = time_lag['BCET'][:, tech, c2ti['7 O&M ($/MWh)']] * \
                                                                            (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0])
                        data['BCET'][:, tech, c2ti['8 std ($/MWh)']] = time_lag['BCET'][:, tech, c2ti['8 std ($/MWh)']] * \
                                                                            (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0])
            
            # Investment in terms of power technologies:
            for r in range(len(titles['RTI'])):
                data['MWIY'][r, :, 0] = time_lag['MWIY'][r, :, 0] + data['MEWI'][r, :, 0]*data['BCET'][r, :, c2ti['3 Investment ($/kW)']] / 1.33

            # =====================================================================
            # Cost-supply curve
            # =====================================================================

            bcet, bcsc, mewl, mepd, merc, rery, mred, mres = cost_curves(
                data['BCET'], data['MCSC'], data['MEWDX'], data['MEWG'], data['MEWL'], data['MEPD'],
                data['MERC'], time_lag['MERC'], data['RERY'], data['MPTR'], data['MRED'], data['MRES'],
                titles['RTI'], titles['T2TI'], titles['ERTI'], year, 1.0
                )

            data['BCET'] = bcet
            data['MCSC'] = bcsc
            data['MEWL'] = mewl
            data['MEPD'] = mepd
            data['MERC'] = merc
            data['RERY'] = rery
            data['MRED'] = mred
            data['MRES'] = mres
            
            # Take into account curtailment again:
            data["MEWL"] = data["MEWL"] * (1 - data["MCTN"])
            data['BCET'][:, :, c2ti['11 Decision Load Factor']]  *= (1 - data["MCTN"][:, :, 0])
            
            # =====================================================================
            # Initialise the LCOE variables
            # =====================================================================
            data = get_lcoe(data, titles)
            # Historical differences between demand and supply.
            # This variable covers transmission losses and net exports
            # Hereafter, the lagged variable will have these values stored
            # We assume that the values do not change throughout simulation.
    #        data['MELO'][:, 0, 0] = data['MEWG'][:,:,0].sum(axis=1) - tot_elec_dem
            data["MWDL"] = time_lag["MEWDX"]        # Save so that you can access twice lagged demand
            print("")
            print(f"In year {year}, MERC onshore is {data['MERC'][0, 9, 0]:5f}")
            print(f"In year {year}, MCTN onshore is {data['MCTN'][0, 16, 0]:5f}")
            print(f"In year {year}, MEWL onshore is {data['MEWL'][0, 16, 0]:5f}")
            print(f"In year {year}, MEWW onshore is {data['MEWW'][0, 16, 0]:5f}")

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

                data_dt[var] = np.copy(time_lag[var])

        data_dt['MWIY'] = np.zeros([len(titles['RTI']), len(titles['T2TI']), 1])

        # Create new regulation variable for emulation
        isReg = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
        isReg = data['MEWR'][:, :, 0]
        
        # Create the regulation variable
        # division = np.zeros_like(data_dt['MEWR'][:, :, 0])
        # np.divide((data_dt['MEWK'][:, :, 0] - data['MEWR'][:, :, 0]), data['MEWR'][:, :, 0], \
        #           out=division, where=data['MEWR'][:, :, 0]>0)
        # isReg = 0.5 + 0.5*np.tanh(1.5+10* division)
       

        # isReg[data['MEWR'][:, :, 0] == 0.0] = 1.0
        # isReg[data['MEWR'][:, :, 0] == -1.0] = 0.0

        # Call the survival function routine.
#        data = survival_function(data, time_lag, histend, year, titles)

        # Total number of scrapped techicles:
#        tot_eol = np.sum(data['MEOL'][:, :, 0], axis=1)

        # Total capacity additions
#        data['MWIA'][:, 0, 0] = (data['PG_TTC'][:, 0, 0]
#                                   - time_lag['PG_TTC'][:, 0, 0]
#                                   + tot_eol)
#        data['MWIA'][:, 0, 0][data['MEWKA'][:, 0, 0] < 0.0] = 0.0

        # Number of timesteps no_it and timestep size dt
        no_it = int(data['noit'][0, 0, 0])
        dt = 1 / float(no_it)

        data["MWDL"] = time_lag["MEWDX"]             # Save so that you can access twice lagged demand
        growth_rate = 1 + (time_lag["MEWDX"][:, 7, 0] - time_lag["MWDL"][:, 7, 0])/time_lag["MWDL"][:, 7, 0]
        
        # =====================================================================
        # Start of the quarterly time-loop
        # =====================================================================

        # Start the computation of shares
        for t in range(1, no_it + 1):

            # Electricity demand is exogenous at the moment
            # TODO: Replace, using price elasticities and feedback from other
            # FTT modules
            
            # Like in FORTRAN, we estimate the growth of demand from extrapolating last year's demand. 
            # MEWDt = time_lag['MEWDX'][:,7,0] + (time_lag['MEWDX'][:, 7, 0] * growth_rate - time_lag['MEWDX'][:, 7, 0]) * t/no_it
            
            # Given that we know the demand at the end of the year, we can alternatively cheat for additional accuracy
            MEWDt = time_lag['MEWDX'][:,7,0] + (data['MEWDX'][:, 7, 0] - time_lag['MEWDX'][:, 7, 0]) * t/no_it
            
            MEWDt += data_dt['MADG'][:,0,0] * 0.0036
            e_demand = MEWDt * 1000/3.6

            
            # For checking
            if t == no_it:
                data["MEWD"] = np.copy(data['MEWDX'])
            

            # =================================================================
            # Shares equation
            # =================================================================
            mews, mewl, mewg, mewk = shares(dt, t, T_Scal, MEWDt,
                                            data_dt['MEWS'], data_dt['METC'],
                                            data_dt['MTCD'], data['MWKA'],
                                            data_dt['MES1'], data_dt['MES2'],
                                            data['MEWA'], isReg, data_dt['MEWK'],
                                            time_lag['MEWK'], data['MEWR'],
                                            data_dt['MEWL'], time_lag['MEWS'],
                                            data['MWLO'],
                                            len(titles['RTI']), len(titles['T2TI']), no_it)
            data['MEWS'] = mews
            data['MEWL'] = mewl
            data['MEWG'] = mewg
            data['MEWK'] = mewk
            
            # if year in [2021, 2022]:
            #     print(f'Belgium MEWD {year}:{t} is {data["MEWD"][1, 7, 0]:.0f} after shares')
            #     print(f'Belgium MEWDt {year}:{t} is {MEWDt[0]:.0f} after shares')
            #     print(f'Belgium solar MEWG in {year}:{t} is {data["MEWG"][0, 18, 0]:.0f} after shares')
                #print(f'Sum solar MEWS in {year}:{t} is {np.sum(data["MEWS"][:, 18]):.1f} after shares')
            # if year in [2049, 2050]:
            #     print(f'Sum solar MEWK in {year}:{t} is {np.sum(data["MEWK"][:, 18]):.0f} after shares')
                #print(f'Sum solar MEWS in {year}:{t} is {np.sum(data["MEWS"][:, 18]):.1f} after shares')
            
            if np.any(np.isnan(data['MEWS'])):
                print(f"NaNs found in MEWS in {year}")
            if ~np.any(np.isclose(data['MEWS'][:,:,0].sum(axis=1), 1.0)):
                print(f"Sum of MEWS does not add up to 1 in {year}")
            if np.any(data['MEWS'][:,:,0]< 0.0):
                print(f"Negative MEWS found in {year}")
                r_err, t_err = np.unravel_index(np.nanargmin(data['MEWS'][:,:,0]), data['MEWS'][:,:,0].shape)
                
                print(data['MEWS'][r_err, t_err, 0], titles['RTI'][r_err], titles["T2TI"][t_err])

            # =================================================================
            # Residual load-duration curve
            # =================================================================
            # Call RLDC function for capacity and load factor by LB, and storage costs
            data = rldc(data, time_lag, data_dt, year, titles)
            
            # Change currency from EUR2015 to USD2013 (This is wrong, but in terms of logic and by misstating currency year for storage)
            data['MSSP'][:, :, 0] = data['MSSP'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis]) / data['EX13'][33, 0, 0]
            data['MLSP'][:, :, 0] = data['MLSP'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis]) / data['EX13'][33, 0, 0]
            data['MSSM'][:, :, 0] = data['MSSM'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis]) / data['EX13'][33, 0, 0]
            data['MLSM'][:, :, 0] = data['MLSM'][:, :, 0] * (data['PRSC13'][:, 0, 0, np.newaxis]/data['PRSC15'][:, 0, 0, np.newaxis]) / data['EX13'][33, 0, 0]


            # =================================================================
            # Dispatch routine
            # =================================================================
            # Call DSPCH function to dispatch flexible capacity based on MC

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
                nonzero_cap = np.sum(klb3, axis=1) > 0
                data['MEWL'][r, nonzero_cap, 0] = np.sum(glb3[nonzero_cap,:], axis=1) / np.sum(klb3[nonzero_cap,:], axis=1)
                # Generation by load band
                data['MWG1'][r, :, 0] = glb3[:, 0]
                data['MWG2'][r, :, 0] = glb3[:, 1]
                data['MWG3'][r, :, 0] = glb3[:, 2]
                data['MWG4'][r, :, 0] = glb3[:, 3]
                data['MWG5'][r, :, 0] = glb3[:, 4]
                data['MWG6'][r, :, 0] = glb3[:, 5]
                # To avoid division by 0 or near 0, if very low shares
                zero_lf = data['MEWL'][r,:,0] <= 0.0001
                data['MEWL'][r, zero_lf, 0] = data["MWLO"][r, zero_lf, 0]

                # Re-calculate capacities
#                data['MEWK'][r, :, 0] = divide(data['MEWG'][r, :, 0], data['MEWL'][r, :, 0])/8766

            # =============================================================
            #  Update variables wrt curtailment
            # =============================================================

            # Adjust capacity factors for VRE due to curtailment, and to cover efficiency losses during
            # Gross Curtailed electricity
            data['MCGA'][:,0,0] = data['MCRT'][:,0,0] * np.sum(Svar * data['MEWG'][:,:,0], axis=1)

            # Net curtailed generation
            # Remove long-term storage demand and assume that at least 45% of gross curtailment is retained.
            # On average 45% of curtailed electricity can be reused for long-term storage:
            # Source: https://www.frontiersin.org/articles/10.3389/fenrg.2020.527910/full
            data['MCNA'][:, 0, 0] = np.maximum(data['MCGA'][:, 0, 0] - 0.45*2*data['MLSG'][:,0,0], 0.55*data['MCGA'][:,0,0])
            # Impact of net curtailment on load factors for VRE technologies
            # Scale down the curtailment rate by taking into account the electricity that is actually used for long-term storage
            data['MCTN'][:,:,0] = data['MCTG'][:,:,0] * divide(data['MCNA'][:, :, 0],
                                                               data['MCGA'][:, :, 0])
            
            if year == 2050 and t == no_it:
                print(f"Total solar MEWL in 2050 is: {np.sum(data['MEWL'][:70, 18, 0]):.4f}")

            
            # Total additional electricity that needs to be generated
            data['MADG'][:,0,0] = data['MCGA'][:,0,0] - data['MCNA'][:, 0, 0] + data['MSSG'][:,0,0]
            
            # Update generation
            denominator = np.sum(data['MEWS'][:, :, 0] * data['MEWL'][:, :, 0], axis=1)[:, np.newaxis]
            updated_e_sup = e_demand[:] + data['MADG'][:, 0, 0] - data_dt['MADG'][:, 0, 0]
            data['MEWG'][:, :, 0] = divide(data['MEWS'][:, :, 0] * updated_e_sup[:, np.newaxis] * data['MEWL'][:, :, 0],
                                           denominator) 

            # Update capacities
            data['MEWK'] = divide(data['MEWG'], data['MEWL']) / 8766
            # Update emissions
            data['MEWE'][:, :, 0] = data['MEWG'][:, :, 0] * data['BCET'][:, :, c2ti['15 Emissions (tCO2/GWh)']] / 1e6
            
            # Update investment. Note that sum(mewi_t) not exactly mewi
            _, mewi_t = get_sales(
                data["MEWK"], data_dt["MEWK"], time_lag["MEWK"], data["MEWS"], 
                data_dt["MEWS"], data["MEWI"], data['BCET'][:, :, c2ti["9 Lifetime (years)"]], dt)
            
            data["MEWI"] = get_sales_yearly(
                data["MEWK"], time_lag["MEWK"], data["MEWS"], time_lag["MEWS"],
                data["MEWI"], data['BCET'][:, :, c2ti["9 Lifetime (years)"]])
            

            earlysc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])
            lifetsc = np.zeros([len(titles['RTI']), len(titles['T2TI'])])

            for r in range(len(titles['RTI'])):
            # TODO: Clean this up - for now just an ugly loop
                for tech in range(len(titles['T2TI'])):

                    if data['MEWK'][r, tech, 0] - data_dt['MEWK'][r, tech, 0] >= 0.0:

                        earlysc[r, tech] = 0.0
                        lifetsc[r, tech] = data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']]
                        data['MESC'][r, tech, 0] = 0.0

                    else:

                        earlysc[r, tech] = data['MEWK'][r, tech, 0] - data_dt['MEWK'][r, tech, 0]
                        lifetsc[r, tech] = ((1.0 - data['MEWK'][r, tech, 0]/np.sum(data['MEWK'][r, :, 0])) 
                                            * (data['MEWK'][r, tech, 0] / earlysc[r, tech]) * 5 )

                    if (lifetsc[r, tech] - data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']]) < 0.0:

                        data['MESC'][r, tech, 0] = -earlysc[r, tech] * (
                                (data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']] - lifetsc[r, tech]) /
                                data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']] *
                                data_dt['BCET'][r, tech, c2ti['3 Investment ($/kW)']])

                        data['MELF'][r, tech, 0] = lifetsc[r, tech]

                    else:

                        data['MESC'][r, tech, 0] = 0.0
                        data['MELF'][r, tech, 0] = data_dt['BCET'][r, tech, c2ti['9 Lifetime (years)']]

            # =============================================================
            # Learning-by-doing
            # =============================================================

            # Cumulative global learning
            # Using a technological spill-over matrix (PG_SPILL) together with capacity
            # additions (PG_CA) we can estimate total global spillover of similar techs
            mewi0 = np.sum(mewi_t[:, :, 0], axis=0)
            dw = np.zeros(len(titles["T2TI"]))
            
            
            for i in range(len(titles["T2TI"])):
                dw_temp = np.copy(mewi0)
                dw_temp[dw_temp > dw_temp[i]] = dw_temp[i]
                dw[i] = np.dot(dw_temp, data['MEWB'][0, i, :])


            # Cumulative capacity incl. learning spill-over effects
            data["MEWW"][0, :, 0] = data_dt['MEWW'][0, :, 0] + dw
           

            # Copy over the technology cost categories. We update the investment and capacity factors below
            data['BCET'][:, :, 1:17] = time_lag['BCET'][:, :, 1:17].copy()

            # Store gamma values in the cost matrix (in case it varies over time)
            data['BCET'][:, :, c2ti['21 Gamma ($/MWh)']] = data['MGAM'][:, :, 0]

            # Add in carbon costs due to EU ETS
            #data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = copy.deepcopy(data['MCOCX'][:, :, 0])
            convert_cp = (data['REPP'][:,0,0]/(data['PRSC'][:,0,0]/data['EX'][:,0,0])/(data['PRSC13'][:,0,0]/data['EX13'][:,0,0])*data['REX13'][33,0,0])/(1000*3.666)
            data['BCET'][:, :, c2ti['1 Carbon Costs ($/MWh)']] = data['BCET'][:, :, 14] * convert_cp[:, np.newaxis]          

            # Learning-by-doing effects on investment
            for tech in range(len(titles['T2TI'])):

                if data['MEWW'][0, tech, 0] > 0.001:

                    data['BCET'][:, tech, c2ti['3 Investment ($/kW)']] = (
                            data_dt['BCET'][:, tech, c2ti['3 Investment ($/kW)']] 
                            * (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0]))
                    data['BCET'][:, tech, c2ti['4 std ($/MWh)']] = (
                            data_dt['BCET'][:, tech, c2ti['4 std ($/MWh)']] 
                             *  (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0]))
                    data['BCET'][:, tech, c2ti['7 O&M ($/MWh)']] = (
                            data_dt['BCET'][:, tech, c2ti['7 O&M ($/MWh)']] 
                             * (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0]))
                    data['BCET'][:, tech, c2ti['8 std ($/MWh)']] = (
                            data_dt['BCET'][:, tech, c2ti['8 std ($/MWh)']] 
                            * (1.0 + data['BCET'][:, tech, c2ti['16 Learning exp']] * dw[tech]/data['MEWW'][0, tech, 0]))
            
            
            # Investment (1.33 an exchange rate factor, code differs from FORTRAN)
            data['MWIY'][:, :, 0] = (data_dt['MWIY'][:, :, 0]
                                     + (data['MEWI'][:, :, 0] * dt * data['BCET'][:, :, c2ti['3 Investment ($/kW)']] / 1.33))
            

            # =================================================================
            # Cost-Supply curves
            # =================================================================  
           
            bcet, bcsc, mewl, mepd, merc, rery, mred, mres = cost_curves(
                data['BCET'], data['MCSC'], data['MEWDX'], data['MEWG'], data['MEWL'], data['MEPD'],
                data['MERC'], time_lag['MERC'], data['RERY'], data['MPTR'], data['MRED'], data['MRES'],
                titles['RTI'], titles['T2TI'], titles['ERTI'], year, dt
                )

            data['BCET'] = bcet
            data['MCSC'] = bcsc
            data['MEWL'] = mewl
            data['MEPD'] = mepd
            data['MERC'] = merc
            data['RERY'] = rery
            data['MRED'] = mred
            data['MRES'] = mres
            
            
            # Take into account curtailment, computed above:
            data["MEWL"] = data["MEWL"] * (1 - data["MCTN"])
            data['BCET'][:, :, c2ti['11 Decision Load Factor']]  *= (1 - data["MCTN"][:, :, 0])
            
            
            # =================================================================
            # Update LCOE
            # =================================================================
            data = get_lcoe(data, titles)

            # =================================================================
            # Update the time-loop variables data_dt
            # =================================================================

            for var in data_dt.keys():

                if domain[var] == 'FTT-P':

                    data_dt[var] = np.copy(data[var])
        
        if year == 2050 and t == no_it:
            print(f"Total solar in 2050 is: {np.sum(data['MEWG'][:, 18, 0])/10**6:.3f}M")
            print(f"Final total solar MEWL in 2050 is: {np.sum(data['MEWL'][:70, 18, 0]):.4f}")


    return data
