# -*- coding: utf-8 -*-
"""
=========================================
ftt_nmm_main.py
=========================================
Industrial non-metallic minerals sector FTT module.
###################################################


This is the main file for FTT: Industrial Heat - NMM, which models technological
diffusion of industrial heat processes within the non-metallic minerals sector due
to simulated investor decision making. Investors compare the **levelised cost of
industrial heat**, which leads to changes in the market shares of different technologies.

The outputs of this module include changes in final energy demand and emissions due
chemical heat processes for the EU28.

Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Bespoke element-wise divide which replaces divide-by-zeros with zeros

Functions included:

    - solve
        Main solution function for the module
    - get_lcoih
        Calculates the levelised cost of industrial heat

"""
# Standard library imports
from math import sqrt
import os
import copy
import sys
import warnings
import time

# Third party imports
import pandas as pd
import numpy as np

# Local library imports
from SourceCode.support.divide import divide

# %% lcoh
# -----------------------------------------------------------------------------
# --------------------------- LCOH function -----------------------------------
# -----------------------------------------------------------------------------
def get_lcoih(data, titles, year):
    """
    Calculate levelized costs.

    The function calculates the levelised cost of industrial heat in 2019 Euros
    It includes intangible costs (gamma values) and together
    determines the investor preferences.

    Parameters
    -----------
    data: dictionary
        Data is a container that holds all cross-sectional (of time) for all
        variables. Variable names are keys and the values are 3D NumPy arrays.
    titles: dictionary
        Titles is a container of all permissible dimension titles of the model.

    Returns
    ----------
    data: dictionary
        Data is a container that holds all cross-sectional (of time) data for
        all variables.
        Variable names are keys and the values are 3D NumPy arrays.
        The values inside the container are updated and returned to the main
        routine.

    Notes
    ---------
    Additional notes if required.
    """
    sector = 'NMM'
    # Categories for the cost matrix (BIC4)
    ctti = {category: index for index, category in enumerate(titles['CTTI'])}

    for r in range(len(titles['RTI'])):
        if data['IUD4'][r, :, 0].sum(axis=0)==0:
            continue


        lt = data['BIC4'][r,:, ctti['5 Lifetime (years)']]
        max_lt = int(np.max(lt))
        lt_mat = np.linspace(np.zeros(len(titles['ITTI'])), max_lt-1,
                             num=max_lt, axis=1, endpoint=True)
        lt_max_mat = np.concatenate(int(max_lt)*[lt[:, np.newaxis]], axis=1)
        mask = lt_mat < lt_max_mat
        lt_mat = np.where(mask, lt_mat, 0)



        # Capacity factor used in decisions (constant), not actual capacity factor #TODO ask about this
        cf = data['BIC4'][r,:, ctti['13 Capacity factor mean'], np.newaxis]

        #conversion efficiency
        ce = data['BIC4'][r,:, ctti['9 Conversion efficiency'], np.newaxis]

        # Trap for very low CF
        cf[cf<0.000001] = 0.000001

        # Factor to transfer cost components in terms of capacity to generation
#        ones = np.ones([len(titles['ITTI']), 1])
        conv = 1/(cf)/8766 #number of hours in a year

        # Discount rate
        # dr = data['BIC4'][r,6]
        dr = data['BIC4'][r,:, ctti['8 Discount rate'], np.newaxis]

        # Initialse the levelised cost components
        # Average investment cost
        it = np.zeros([len(titles['ITTI']), int(max_lt)])
        it[:, 0, np.newaxis] =  data['BIC4'][r,:, ctti['1 Investment cost mean (MEuro per MW)'], np.newaxis] * conv*(1*10^6)


        # Standard deviation of investment cost
        dit = np.zeros([len(titles['ITTI']), int(max_lt)])
        dit[:, 0, np.newaxis] =  data['BIC4'][r,:, ctti['2 Investment cost SD'], np.newaxis] * conv*(1*10^6)


        # Subsidies as a percentage of investment cost
        st = np.zeros([len(titles['ITTI']), int(max_lt)])
        st[:, 0, np.newaxis] = (data['BIC4'][r,:, ctti['1 Investment cost mean (MEuro per MW)'], np.newaxis]
             * data['ISB4'][r, :, 0,np.newaxis] * conv)*(1*10^6)


        # Average fuel costs 2010Euros/toe to euros/MWh 1 toe = 11.63 MWh
        ft = np.ones([len(titles['ITTI']), int(max_lt)])
        ft = ft * data['BIC4'][r,:, ctti['10 Fuel cost mean'], np.newaxis]/11.63/ce
        ft = np.where(mask, ft, 0)

        # Standard deviation of fuel costs
        dft = np.ones([len(titles['ITTI']), int(max_lt)])
        dft = dft * data['BIC4'][r,:, ctti['11 Fuel cost SD'], np.newaxis]/11.63/ce
        dft = np.where(mask, dft, 0)

        #fuel tax/subsidies
        ftt = np.ones([len(titles['ITTI']), int(max_lt)])
        ftt = ftt * data['IFT4'][r,:, 0, np.newaxis]/11.63/ce
        ftt = np.where(mask, ftt, 0)

        # Fixed operation & maintenance cost - variable O&M available but not included
        omt = np.ones([len(titles['ITTI']), int(max_lt)])
        omt = omt * data['BIC4'][r,:, ctti['3 O&M cost mean (Euros/MJ/s/year)'], np.newaxis]*conv #(euros per MW) in a year
        omt = np.where(mask, omt, 0)

        # Standard deviation of operation & maintenance cost
        domt = np.ones([len(titles['ITTI']), int(max_lt)])
        domt = domt * data['BIC4'][r,:, ctti['4 O&M cost SD'], np.newaxis]*conv
        domt = np.where(mask, domt, 0)



        # Net present value calculations
        # Discount rate
        denominator = (1+dr)**lt_mat

        # 1-Expenses
        # 1.1-Without policy costs
        npv_expenses1 = (it+ft+omt)/denominator
        # 1.2-With policy costs
        npv_expenses2 = (it+st+ft+ftt+omt)/denominator
        # 1.3-Only policy costs
        #npv_expenses3 = (st+fft-fit)/denominator
        # 2-Utility
        npv_utility = 1/denominator
        #Remove 1s for tech with small lifetime than max but keep t=0 as 1
        npv_utility[npv_utility==1] = 0
        npv_utility[:,0] = 1
        # 3-Standard deviation (propagation of error)
        npv_std = np.sqrt(dit**2 + dft**2 + domt**2)/denominator

        # 1-levelised cost variants in $/pkm
        # 1.1-Bare LCOT

        lcoe = np.sum(npv_expenses1, axis=1)/np.sum(npv_utility, axis=1)

        # 1.2-LCOT including policy costs
        tlcoe = np.sum(npv_expenses2, axis=1)/np.sum(npv_utility, axis=1)#+data['IEFI'][r, :, 0]
        # 1.3 LCOE excluding policy, including co2 price
        #lcoeco2 = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)
        # 1.3-LCOT of policy costs
        # lcoe_pol = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)+data['MEFI'][r, :, 0]
        # Standard deviation of LCOT
        dlcoe = np.sum(npv_std, axis=1)/np.sum(npv_utility, axis=1)

        # LCOE augmented with gamma values
        tlcoeg = tlcoe+data['IAM4'][r, :, 0]

        if np.any(tlcoeg < 0.0):
                    msg = """Sector: {} - Region: {} - Year: {}
                    Negative levelised cost detected! Critical error!
                    """.format(sector, titles['RTI'][r], year)
                    warnings.warn(msg)

        # Pass to variables that are stored outside.
        data['ILC4'][r, :, 0] = lcoe            # The real bare LC without taxes (euros/mwh)
        #data['IHLT'][r, :, 0] = tlcoe           # The real bare LC with taxes
        data['ILG4'][r, :, 0] = tlcoeg         # As seen by consumer (generalised cost)
        data['ILD4'][r, :, 0] = dlcoe          # Variation on the LC distribution



    return data

#Final energy demand has to match IEA

# %% main function
# -----------------------------------------------------------------------------
# ----------------------------- Main ------------------------------------------
# -----------------------------------------------------------------------------
def solve(data, time_lag, iter_lag, titles, histend, year, domain):#, #specs, converter, coefficients):
    """

    Main solution function for the module.

    Simulates investor decision making.

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
    specs: dictionary of NumPy arrays
        Function specifications for each region and module

    Returns
    ----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution


    """

    # Categories for the cost matrix (BIC4)
    ctti = {category: index for index, category in enumerate(titles['CTTI'])}

    sector = 'NMM'

    cost_data_year = 2020


    data = get_lcoih(data, titles, year)

    # Endogenous calculation takes over from here
    if year > histend['IUD4']:

        # Create a local dictionary for timeloop variables
        # It contains values between timeloop interations in the FTT core
        data_dt = {}

        # First, fill the time loop variables with the their lagged equivalents
        for var in time_lag.keys():

            data_dt[var] = copy.deepcopy(time_lag[var])

        # Create the regulation variable #Regulate capacity #no regulations yet, isReg full of zeros
        division = divide((data_dt['IWK4'][:, :, 0] - data['IRG4'][:, :, 0]),
                        data_dt['IRG4'][:, :, 0]) # divide gives 0 when dividing by 0
        isReg = 0.5 + 0.5*np.tanh(1.5+10*division)
        isReg[data['IRG4'][:, :, 0] == 0.0] = 1.0
        isReg[data['IRG4'][:, :, 0] == -1.0] = 0.0


        # Factor used to create quarterly data from annual figures
        no_it = int(data['noit'][0,0,0])
        dt = 1 / float(no_it)
        kappa = 10 #tech substitution constant

        ############## Computing new shares ##################

        IUD4tot = data['IUD4'][:, :, 0].sum(axis=1)
        #Start the computation of shares
        for t in range(1, no_it+1):

            # Interpolate to prevent staircase profile.
            #Time lagged UED plus change in UED * (no of iterations) * dt

            IUD4t = time_lag['IUD4'][:, :, 0].sum(axis=1) + (IUD4tot - time_lag['IUD4'][:, :, 0].sum(axis=1)) * t * dt
            IUD4lt = time_lag['IUD4'][:, :, 0].sum(axis=1) + (IUD4tot - time_lag['IUD4'][:, :, 0].sum(axis=1)) * (t-1) * dt

            for r in range(len(titles['RTI'])):

                if IUD4t[r] == 0.0:
                    continue



            ############################ FTT ##################################

                # DSiK contains the change in shares
                dSik = np.zeros([len(titles['ITTI']), len(titles['ITTI'])])

                # F contains the preferences
                F = np.ones([len(titles['ITTI']), len(titles['ITTI'])])*0.5

                # Market share constraints
                Gijmax = np.ones(len(titles['ITTI']))
                #Gijmin = np.ones((t2ti))

                # -----------------------------------------------------
                # Step 1: Endogenous EOL replacements
                # -----------------------------------------------------
                for b1 in range(len(titles['ITTI'])):

                    if  not (data_dt['IWS4'][r, b1, 0] > 0.0 and
                             data_dt['ILG4'][r, b1, 0] != 0.0 and
                             data_dt['ILD4'][r, b1, 0] != 0.0):
                        continue

                    #TODO: create market share constraints
                    Gijmax[b1] = 0.5 + 0.5*np.tanh(1.25*(data_dt['ISC4'][r, b1, 0] - data_dt['IWS4'][r, b1, 0])/0.1)
                    #Gijmin[b1] = np.tanh(1.25*(-mes2_dt[r, b1, 0] + mews_dt[r, b1, 0])/0.1)



                    S_i = data_dt['IWS4'][r, b1, 0]


                    for b2 in range(b1):

                        if  not (data_dt['IWS4'][r, b2, 0] > 0.0 and
                                 data_dt['ILG4'][r, b2, 0] != 0.0 and
                                 data_dt['ILD4'][r, b2, 0] != 0.0):
                            continue

                        S_k = data_dt['IWS4'][r,b2, 0]
                        Aik = data['IWA4'][0,b1 , b2]*kappa
                        Aki = data['IWA4'][0,b2, b1]*kappa

                        # Propagating width of variations in perceived costs
                        dFik = sqrt(2) * sqrt((data_dt['ILD4'][r, b1, 0]*data_dt['ILD4'][r, b1, 0] + data_dt['ILD4'][r, b2, 0]*data_dt['ILD4'][r, b2, 0]))

                        # Consumer preference incl. uncertainty
                        Fik = 0.5*(1+np.tanh(1.25*(data_dt['ILG4'][r, b2, 0]-data_dt['ILG4'][r, b1, 0])/dFik))

                        # Preferences are then adjusted for regulations
                        F[b1, b2] = Fik*(1.0-isReg[r, b1]) * (1.0 - isReg[r, b2]) + isReg[r, b2]*(1.0-isReg[r, b1]) + 0.5*(isReg[r, b1]*isReg[r, b2])
                        F[b2, b1] = (1.0-Fik)*(1.0-isReg[r, b2]) * (1.0 - isReg[r, b1]) + isReg[r, b1]*(1.0-isReg[r, b2]) + 0.5*(isReg[r, b2]*isReg[r, b1])


                        #Runge-Kutta market share dynamiccs
                        k_1 = S_i*S_k * (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])
                        k_2 = (S_i+dt*k_1/2)*(S_k-dt*k_1/2)* (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])
                        k_3 = (S_i+dt*k_2/2)*(S_k-dt*k_2/2) * (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])
                        k_4 = (S_i+dt*k_3)*(S_k-dt*k_3) * (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])

                        #This method currently applies RK4 to the shares, but all other components of the equation are calculated for the overall time step
                        #We must assume the the LCOE does not change significantly in a time step dt, so we can focus on the shares.

                        dSik[b1, b2] = dt*(k_1+2*k_2+2*k_3+k_4)/6
                        dSik[b2, b1] = -dSik[b1, b2]

                #calculate temportary market shares and temporary capacity from endogenous results
                endo_shares = data_dt['IWS4'][r, :, 0] + np.sum(dSik, axis=1) 
                endo_ued = endo_shares * IUD4t[r, np.newaxis]


                # -----------------------------------------------------
                # Step 3: Exogenous sales additions
                # -----------------------------------------------------
                # Add in exogenous sales figures. These are blended with endogenous result!


                # Add in exogenous sales figures. These are blended with
                # endogenous result! Note that it's different from the
                # ExogSales specification!
                Utot = IUD4t[r]
                
                dSk = np.zeros((len(titles['ITTI'])))
                dUk = np.zeros((len(titles['ITTI'])))
                dUkTK = np.zeros((len(titles['ITTI'])))
                dUkREG = np.zeros((len(titles['ITTI'])))

                # Convert exogenous share changes to capcity/useful energy demand. They do not need to sum to one.
                dUkTK = data['IXS4'][r, :, 0]*Utot/no_it

                #Check endogenous capacity plus additions for a single time step does not exceed regulated capacity.
                #Convert ued to capcity for this check
                reg_vs_exog = ((dUkTK + endo_ued)/data['BIC4'][r, :, ctti["13 Capacity factor mean"]]/8766 > data['IRG4'][r, :, 0]) & (data['IRG4'][r, :, 0] >= 0.0)
                dUkTK = np.where(reg_vs_exog, 0.0, dUkTK)


                # Correct for regulations due to the stretching effect. This is the difference in ued due only to demand increasing.
                # This will be the difference between ued based on the endogenous ued, and what the endogenous ued would have been
                # if total demand had not grown.

                dUkREG = np.where((endo_ued - endo_shares*IUD4lt[r,np.newaxis])>0.0,-(endo_ued - endo_shares*IUD4lt[r,np.newaxis])*isReg[r, :].reshape([len(titles['ITTI'])]),0.0)


                # Sum effect of exogenous sales additions (if any) with
                # effect of regulations
                #Note that the share of indirect heating vs direct must be preserved
                indirect_cut_off = 7
                dUk = dUkREG + dUkTK
                dUtot_indirect = np.sum(dUk[:indirect_cut_off])
                dUtot_direct = np.sum(dUk[indirect_cut_off:])

                indirect_shares = divide((endo_ued[:indirect_cut_off] + dUk[:indirect_cut_off]),(np.sum(endo_ued[:indirect_cut_off])+dUtot_indirect))
                direct_shares = divide((endo_ued[indirect_cut_off:] + dUk[indirect_cut_off:]),(np.sum(endo_ued[indirect_cut_off:])+dUtot_direct))
                indirect_weighting = np.sum(endo_shares[:indirect_cut_off])
                

                # Calculate changes to endogenous ued, and use to find new market shares
                # Zero ued will result in zero shares
                # All other ueds will be streched



                data['IWS4'][r, :indirect_cut_off, 0] = indirect_shares*indirect_weighting
                data['IWS4'][r, indirect_cut_off:, 0] = direct_shares*(1-indirect_weighting)


                if ~np.isclose(np.sum(data['IWS4'][r, :, 0]), 1.0, atol=1e-5):
                    msg = """Sector: {} - Region: {} - Year: {}
                    Sum of market shares do not add to 1.0 (instead: {})
                    """.format(sector, titles['RTI'][r], year, np.sum(data['IWS4'][r, :, 0]))
                    warnings.warn(msg)

                if np.any(data['IWS4'][r, :, 0] < 0.0):
                    msg = """Sector: {} - Region: {} - Year: {}
                    Negative market shares detected! Critical error!
                    """.format(sector, titles['RTI'][r], year)
                    warnings.warn(msg)




            # =============================================================
            #  Update variables
            # =============================================================

            #TODO: what else needs to go here? TODO calculate new capacity and new yearly capacity change

            #Useful heat by technology, calculate based on new market shares #Regional totals
            data['IUD4'][:, :, 0] = data['IWS4'][:, :, 0]* IUD4t[:, np.newaxis]

            # Capacity by technology
            data['IWK4'][:, :, 0] = divide(data['IUD4'][:, :, 0],
                                              data['BIC4'][:, :, ctti["13 Capacity factor mean"]]*8766)
            
            
            #Investment by technology, based on eol replacements 
            breakdowns = divide(time_lag['IWK4'][:, :, 0]*dt,
                                                            data['BIC4'][:, :, ctti['5 Lifetime (years)']])

            breakdowns_partial = (data['IWS4'][:, :, 0]  - (data_dt['IWS4'][:, :, 0] - 
                                                    divide(data_dt['IWS4'][:, :, 0]*dt,data['BIC4'][:, :, ctti['5 Lifetime (years)']])))*time_lag['IWK4'][:, :, 0]
            
            eol_condition = data['IWS4'][:, :, 0]  - data_dt['IWS4'][:, :, 0] >= 0.0

            eol_condition_partial = (-breakdowns < data['IWS4'][:, :, 0]  - data_dt['IWS4'][:, :, 0]) & (data['IWS4'][:, :, 0]  - data_dt['IWS4'][:, :, 0]< 0.0)

            eol_replacements_t = np.where(eol_condition, breakdowns, 0.0)
            
            eol_replacements_t = np.where(eol_condition_partial, breakdowns_partial, eol_replacements_t)

            investment_t = np.where((data['IWK4'][:, :, 0]-data_dt['IWK4'][:, :, 0]) > 0, 
                data['IWK4'][:, :, 0]-data_dt['IWK4'][:, :, 0]+eol_replacements_t, eol_replacements_t)
            
            data['IWI4'][:, :, 0] += investment_t

            #Update emissions
            #IHW4 is the global average emissions per unit of UED (GWh). IHW4 has units of kt of CO2/GWh
            for r in range(len(titles['RTI'])):
                data['IWE4'][r, :, 0] = data['IUD4'][r, :, 0] * data['IHW4'][0, :, 0]


            #Final energy by technology
            data['IFD4'][:, :, 0] = np.where(data['BIC4'][:, :, ctti["9 Conversion efficiency"]] !=0.0,
                                             divide(data['IUD4'][:, :, 0],
                                                    data['BIC4'][:, :, ctti["9 Conversion efficiency"]]),
                                            0.0)

            #Calculate (useful) fuel demand for industrial heat processes by using technology to fuel matrix
            for r in range(len(titles['RTI'])):
                data['IHF4'][r,:,0] = np.matmul(data['IJT4'][0,:,:], data['IFD4'][r,:,0])


            # =============================================================
            # Learning-by-doing
            # =============================================================

            # Cumulative global learning
            # Using a technological spill-over matrix (IEWB spillover matrix) together with capacity
            # additions (IWI4 Capacity additions) we can estimate total global spillover of similar
            # techicals





            bi = np.zeros((len(titles['RTI']),len(titles['ITTI'])))
            for r in range(len(titles['RTI'])):
                bi[r,:] = np.matmul(data['IWB4'][0, :, :],investment_t[r,:])
            dw = np.sum(bi, axis=0)

            # # Cumulative capacity incl. learning spill-over effects
            data["IWW4"][0, :, 0] = data_dt['IWW4'][0, :, 0] + dw
            #
            # # Copy over the technology cost categories that do not change (all except prices which are updated through learning-by-doing below)
            data['BIC4'] = copy.deepcopy(data_dt['BIC4'])
            #
            # # Learning-by-doing effects on investment
            if year > cost_data_year:
                for tech in range(len(titles['ITTI'])):

                    if data['IWW4'][0, tech, 0] > 0.1:

                        data['BIC4'][:, tech, ctti['1 Investment cost mean (MEuro per MW)']] = data_dt['BIC4'][:, tech, ctti['1 Investment cost mean (MEuro per MW)']] * \

                                                                            (1.0 + data['BIC4'][:, tech, ctti['15 Learning exponent']] * dw[tech]/data['IWW4'][0, tech, 0])


            # =================================================================
            # Update the time-loop variables
            # =================================================================

            #Calculate levelised cost again
            data = get_lcoih(data, titles, year)

            #Update time loop variables:
            for var in data_dt.keys():

                data_dt[var] = copy.deepcopy(data[var])


    return data
