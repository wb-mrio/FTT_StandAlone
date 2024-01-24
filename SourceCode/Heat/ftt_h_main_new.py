# -*- coding: utf-8 -*-
"""
=========================================
ftt_h_main.py
=========================================
Residential heating sector FTT module.
######################################

This is the main file for FTT: Heat, which models technological
diffusion of residential heating technologies due to simulated consumer decision making.
Consumers compare the **levelised cost of heat**, which leads to changes in the
market shares of different technologies.

The outputs of this module include changes in final energy demand and boiler sales.

Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Bespoke element-wise divide which replaces divide-by-zeros with zeros
    - `estimation <econometrics_functions.html>`__
        Predict future values according to the estimated coefficients.

Functions included:
    - solve
        Main solution function for the module
    - get_lcoh
        Calculate levelised cost of residential heating

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
def get_lcoh(data, titles):
    """
    Calculate levelized costs.

    The function calculates the levelised cost of heat in 2014 Euros/kWh per
    boiler type. It includes intangible costs (gamma values) and together
    determines the investor preferences.
    """
    # Categories for the cost matrix (BHTC)
    c4ti = {category: index for index, category in enumerate(titles['C4TI'])}

    for r in range(len(titles['RTI'])):

        # Cost matrix
        #bhtc = data['BHTC'][r, :, :]

        # Boiler lifetime
        lt = data['BHTC'][r,:, c4ti['5 Lifetime']]
        max_lt = int(np.max(lt))
        lt_mat = np.linspace(np.zeros(len(titles['HTTI'])), max_lt-1,
                             num=max_lt, axis=1, endpoint=True)
        lt_max_mat = np.concatenate(int(max_lt)*[lt[:, np.newaxis]], axis=1)
        mask = lt_mat < lt_max_mat
        lt_mat = np.where(mask, lt_mat, 0)

        # Capacity factor
        cf = data['BHTC'][r,:, c4ti['13 Capacity factor mean'], np.newaxis]

        # Conversion efficiency
        ce = data['BHTC'][r,:, c4ti['9 Conversion efficiency'], np.newaxis]

        # Discount rate
        dr = data['BHTC'][r,:, c4ti['8 Discount rate'], np.newaxis]

        # Initialse the levelised cost components
        # Average investment cost
        it = np.zeros([len(titles['HTTI']), int(max_lt)])
        # print(it.shape)
        # print(data['BHTC'][r,:, c4ti['1 Investment cost mean']].shape)
        it[:, 0,np.newaxis] = data['BHTC'][r,:, c4ti['1 Inv cost mean (EUR/Kw)'],np.newaxis]/(cf*1000)


        # Standard deviation of investment cost
        dit = np.zeros([len(titles['HTTI']), int(max_lt)])
        dit[:, 0, np.newaxis] = divide(data['BHTC'][r,:, c4ti['2 Inv Cost SD'], np.newaxis], (cf*1000))

        # Upfront subsidy/tax at purchase time
        st = np.zeros([len(titles['HTTI']), int(max_lt)])
        st[:, 0, np.newaxis] = it[:, 0, np.newaxis] * data['HTVS'][r, :, 0, np.newaxis]

        # Average fuel costs
        ft = np.ones([len(titles['HTTI']), int(max_lt)])
        ft = ft * divide(data['BHTC'][r,:, c4ti['10 Fuel cost  (EUR/kWh)'], np.newaxis]*data['HEWP'][r, :, 0, np.newaxis], ce)
        ft = np.where(mask, ft, 0)

        # Standard deviation of fuel costs
        dft = np.ones([len(titles['HTTI']), int(max_lt)])
        dft = dft*ft * data['BHTC'][r,:, c4ti['11 Fuel cost SD'], np.newaxis]
        dft = np.where(mask, dft, 0)

        # Fuel tax costs
        fft = np.ones([len(titles['HTTI']), int(max_lt)])
        fft = fft*data['HTRT'][r, :, 0, np.newaxis]/ce
        fft = np.where(mask, fft, 0)

        # Average operation & maintenance cost
        omt = np.ones([len(titles['HTTI']), int(max_lt)])
        omt = omt * divide(data['BHTC'][r,:, c4ti['3 O&M mean (EUR/kW)'], np.newaxis], (cf*1000))
        omt = np.where(mask, omt, 0)

        # Standard deviation of operation & maintenance cost
        domt = np.ones([len(titles['HTTI']), int(max_lt)])
        domt = domt * divide(data['BHTC'][r,:, c4ti['4 O&M SD'], np.newaxis], (cf*1000))
        domt = np.where(mask, domt, 0)

        # Feed-in-Tariffs
        fit = np.ones([len(titles['HTTI']), int(max_lt)])
        fit = fit * data['HEFI'][r, :, 0, np.newaxis]
        fit = np.where(mask, fit, 0)

        # Net present value calculations
        # Discount rate
        denominator = (1+dr)**lt_mat

        # 1-Expenses
        # 1.1-Without policy costs
        npv_expenses1 = (it+ft+omt)/denominator
        # 1.2-With policy costs
        npv_expenses2 = (it+st+ft+fft+omt-fit)/denominator
        # 1.3-Only policy costs
        npv_expenses3 = (st+fft-fit)/denominator
        # 2-Utility
        npv_utility = 1/denominator
        #Remove 1s for tech with small lifetime than max
        npv_utility[npv_utility==1] = 0
        npv_utility[:,0] = 1
        # 3-Standard deviation (propagation of error)
        npv_std = np.sqrt(dit**2 + dft**2 + domt**2)/denominator

        # 1-levelised cost variants in $/pkm
        # 1.1-Bare LCOT
        lcoh = np.sum(npv_expenses1, axis=1)/np.sum(npv_utility, axis=1)
        # 1.2-LCOT including policy costs
        tlcoh = np.sum(npv_expenses2, axis=1)/np.sum(npv_utility, axis=1)
        # 1.3-LCOT of policy costs
        lcoh_pol = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)
        # Standard deviation of LCOT
        dlcoh = np.sum(npv_std, axis=1)/np.sum(npv_utility, axis=1)

        # LCOT augmented with non-pecuniary costs
        tlcohg = tlcoh + data['HGAM'][r, :, 0]

        # Pay-back thresholds
        # TODO: Titles for FTT:Heat's cost categories are wrong
        pb = data['BHTC'][r,:, c4ti['16 Payback time, mean']]
        dpb = data['BHTC'][r,:, c4ti['17 Payback time, SD']]

        # Marginal costs of existing units
        tmc = ft[:, 0] + omt[:, 0] + fft[:, 0] - fit[:, 0]
        dtmc = np.sqrt(dft[:, 0]**2 + domt[:, 0]**2)

        # Total pay-back costs of potential alternatives
        tpb = tmc + (it[:, 0] + st[:, 0])/pb
        dtpb = np.sqrt(dft[:, 0]**2 + domt[:, 0]**2 +
                       divide(dit[:, 0]**2, pb**2) +
                       divide(it[:, 0]**2, pb**4)*dpb**2)

        # Add gamma values
        tmc = tmc + data['HGAM'][r, :, 0]
        tpb = tpb + data['HGAM'][r, :, 0]

        # Pass to variables that are stored outside.
        data['HEWC'][r, :, 0] = lcoh            # The real bare LCOH without taxes
        data['HETC'][r, :, 0] = tlcoh           # The real bare LCOH with taxes
        data['HGC1'][r, :, 0] = tlcohg         # As seen by consumer (generalised cost)
        data['HWCD'][r, :, 0] = dlcoh          # Variation on the LCOH distribution
        data['HGC2'][r, :, 0] = tmc             # Total marginal costs
        data['HGD2'][r, :, 0] = dtmc          # SD of Total marginal costs
        data['HGC3'][r, :, 0] = tpb             # Total payback costs
        data['HGD3'][r, :, 0] = dtpb          # SD of Total payback costs

    return data

# -----------------------------------------------------------------------------
# ----------------------------- Main ------------------------------------------
# -----------------------------------------------------------------------------
def solve(data, time_lag, iter_lag, titles, histend, year, specs):
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
    specs: dictionary of NumPy arrays
        Function specifications for each region and module

    Returns
    ----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution

    Notes
    ---------
    This function should be broken up into more elements in development.
    """

    # Categories for the cost matrix (BHTC)
    c4ti = {category: index for index, category in enumerate(titles['C4TI'])}
    jti = {category: index for index, category in enumerate(titles['JTI'])}

    fuelvars = ['FR_1', 'FR_2', 'FR_3', 'FR_4', 'FR_5', 'FR_6',
                'FR_7', 'FR_8', 'FR_9', 'FR_10', 'FR_11', 'FR_12']

    sector = 'residential'
    #sector_index = titles['Sectors_short'].index(sector)

    data['PRSC14'] = copy.deepcopy(time_lag['PRSC14'] )
    if year == 2014:
        data['PRSC14'] = copy.deepcopy(data['PRSCX'])


    # %% First initialise if necessary
    # Initialise in case of stock solution specification
    #if np.any(specs[sector]) < 5:

    # Up to the last year of historical useful energy demand by boiler
    if year <= histend['HEWF']:
    # Historical data ends in 2014, so we need to initialise data
    # when it's 2015 to make sure the model runs.
    # At some point we need to change the start year of the simulation and
    # Change the timelines in ALL of the csv's
#        if year == 2015:


        for r in range(len(titles['RTI'])):

            # Useful energy demand by boilers
            data['HEWG'][r, :, 0] = data['HEWF'][r, :, 0] * data['BHTC'][r, :, c4ti["9 Conversion efficiency"]]
            
            # Total useful heat demand
            # This is the demand driver for FTT:Heat
            data['RHUD'][r, 0, 0] = np.sum(data['HEWG'][r, :, 0])
            # print(data['RHUD'][0, :, 0])




            if (data['RHUD'][r, 0, 0] > 0.0):

                # Market shares (based on useful energy demand)
                data['HEWS'][r, :, 0] = data['HEWG'][r, :, 0] / data['RHUD'][r, 0, 0]
                
                # data['HESR'][r, :, 0] = data['HEWF'][r, :, 0] * (data['BHTC'][r, :, c4ti["19 RES calc"]] / np.sum(data['HEWF'][r, :, 0] * data['BHTC'][r, :, c4ti["19 RES calc"]]))

                # CORRECTION TO MARKET SHARES
                # Sometimes historical market shares do not add up to 1.0
                if (~np.isclose(np.sum(data['HEWS'][r, :, 0]), 0.0, atol=1e-9)
                        and np.sum(data['HEWS'][r, :, 0]) > 0.0 ):
                    data['HEWS'][r, :, 0] = np.divide(data['HEWS'][r, :, 0],
                                                       np.sum(data['HEWS'][r, :, 0]))
                # Normalise HEWG to RHUD
                data['HEWG'][r, :, 0] = data['HEWS'][r, :, 0] * data['RHUD'][r, 0, 0]
                # Assuming 'r' is your row index
                # print(data['HEWG'][:10, :, 0])

                
                # Recalculate HEWF based on RHUD
                data['HEWF'][r, :, 0] = data['HEWG'][r, :, 0] / data['BHTC'][r, :, c4ti["9 Conversion efficiency"]]
                    
            # Capacity by boiler
            #Capacity (GW) (13th are capacity factors (MWh/kW=GWh/MW, therefore /1000)
            data['HEWK'][:, :, 0] = divide(data['HEWG'][:, :, 0],
                                  data['BHTC'][:, :, c4ti["13 Capacity factor mean"]])/1000
            # Emissions
            # TODO: Cost titles are wrong
            data['HEWE'][r, :, 0] = data['HEWF'][r, :, 0] * data['BHTC'][r, :, c4ti["15 Emission factor"]]/1e6

            # Final energy demand by energy carrier
            for fuel in range(len(titles['JTI'])):
                # Fuel use for heating
                data['HJHF'][r, fuel, 0] = np.sum(data['HEWF'][r, :, 0] * data['HJET'][0, :, fuel])
                # Fuel use for total residential sector
                if data['HJFC'][r, fuel, 0] > 0.0:
                    data['HJEF'][r, fuel, 0] = data['HJHF'][r, fuel, 0] / data['HJFC'][r, fuel, 0]


    if year == histend['HEWF']:
        # Historical data ends in 2014, so we need to initialise data
        # when it's 2015 to make sure the model runs.
        # At some point we need to change the start year of the simulation and
        # Change the timelines in ALL of the csv's
        # Endogenous price rates
        # endog_price_rate = divide(data['MEWP'][:, :, 0],
        #                           time_lag['MEWP'][:, :, 0])

        # If switch is set to 1, then an exogenous price rate is used
        # Otherwise, the price rates are set to endogenous

        #data['HFPR'][:, :, 0] = copy.deepcopy(data['HFFC'][:, :, 0])

        # Now transform price rates by fuel to price rates by boiler
        #data['HEWP'][:, :, 0] = np.matmul(data['HFFC'][:, :, 0], data['HJET'][0, :, :].T)

        for r in range(len(titles['RTI'])):

            # Final energy demand by energy carrier
            for fuel in range(len(titles['JTI'])):

                # Fuel use for heating
                data['HJHF'][r, fuel, 0] = np.sum(data['HEWF'][r, :, 0] * data['HJET'][0, :, fuel])

                # Fuel use for total residential sector #HFUX is missing
                if data['HJFC'][r, fuel, 0] > 0.0:
                    data['HJEF'][r, fuel, 0] = data['HJHF'][r, fuel, 0] / data['HJFC'][r, fuel, 0]

        # Calculate the LCOT for each vehicle type.
        # Call the function
        data = get_lcoh(data, titles)
# %% Simulation of stock and energy specs
#    t0 = time.time()
    # Stock based solutions first
#    if np.any(specs[sector] < 5):

    # Endogenous calculation takes over from here
    if year > histend['HEWF']:

        # Create a local dictionary for timeloop variables
        # It contains values between timeloop interations in the FTT core
        data_dt = {}

        # First, fill the time loop variables with the their lagged equivalents
        for var in time_lag.keys():
            data_dt[var] = copy.deepcopy(time_lag[var])

        # Create the regulation variable
        division = divide((data_dt['HEWS'][:, :, 0] - data['HREG'][:, :, 0]), data['HREG'][:, :, 0]) # 0 if dividing by 0
        isReg = 0.5 + 0.5*np.tanh(1.5 +10*division)
        isReg[data['HREG'][:, :, 0] == 0.0] = 1.0
        isReg[data['HREG'][:, :, 0] == -1.0] = 0.0

        # Factor used to create quarterly data from annual figures
        no_it = 4
        # int(data['noit'][0,0,0])
        dt = 1 / float(no_it)

        ############## Computing new shares ##################

        #Start the computation of shares
        for t in range(1, no_it+1):

            # Interpolate to prevent staircase profile.
            rhudt = time_lag['RHUD'][:, :, :] + (data['RHUD'][:, :, :] - time_lag['RHUD'][:, :, :]) * t * dt
            rhudlt = time_lag['RHUD'][:, :, :] + (data['RHUD'][:, :, :] - time_lag['RHUD'][:, :, :]) * (t-1) * dt

            for r in range(len(titles['RTI'])):

                if rhudt[r] == 0.0:
                    continue

            ############################ FTT ##################################
#                        t3 = time.time()
#                        print("Solving {}".format(titles["RTI"][r]))
                # Initialise variables related to market share dynamics
                # DSiK contains the change in shares
                dSik = np.zeros([len(titles['HTTI']), len(titles['HTTI'])])

                # F contains the preferences
                F = np.ones([len(titles['HTTI']), len(titles['HTTI'])])*0.5

                # -----------------------------------------------------
                # Step 1: Endogenous EOL replacements
                # -----------------------------------------------------
                for b1 in range(len(titles['HTTI'])):

                    if  not (data_dt['HEWS'][r, b1, 0] > 0.0 and
                             data_dt['HGC1'][r, b1, 0] != 0.0 and
                             data_dt['HWCD'][r, b1, 0] != 0.0):
                        continue

                    S_i = data_dt['HEWS'][r, b1, 0]

                    for b2 in range(b1):

                        if  not (data_dt['HEWS'][r, b2, 0] > 0.0 and
                                 data_dt['HGC1'][r, b2, 0] != 0.0 and
                                 data_dt['HWCD'][r, b2, 0] != 0.0):
                            continue

                        S_k = data_dt['HEWS'][r, b2, 0]

                        # Propagating width of variations in perceived costs
                        dFik = 1.414 * sqrt((data_dt['HWCD'][r, b1, 0]*data_dt['HWCD'][r, b1, 0] + data_dt['HWCD'][r, b2, 0]*data_dt['HWCD'][r, b2, 0]))

                        # Consumer preference incl. uncertainty
                        Fik = 0.5*(1+np.tanh(1.25*(data_dt['HGC1'][r, b2, 0]-data_dt['HGC1'][r, b1, 0])/dFik))

                        # Preferences are then adjusted for regulations
                        F[b1, b2] = Fik*(1.0-isReg[r, b1]) * (1.0 - isReg[r, b2]) + isReg[r, b2]*(1.0-isReg[r, b1]) + 0.5*(isReg[r, b1]*isReg[r, b2])
                        F[b2, b1] = (1.0-Fik)*(1.0-isReg[r, b2]) * (1.0 - isReg[r, b1]) + isReg[r, b1]*(1.0-isReg[r, b2]) + 0.5*(isReg[r, b2]*isReg[r, b1])

                        #Runge-Kutta market share dynamiccs
                        k_1 = S_i*S_k * (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])
                        k_2 = (S_i+dt*k_1/2)*(S_k-dt*k_1/2)* (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])
                        k_3 = (S_i+dt*k_2/2)*(S_k-dt*k_2/2) * (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])
                        k_4 = (S_i+dt*k_3)*(S_k-dt*k_3) * (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])

                        dSik[b1, b2] = dt*(k_1+2*k_2+2*k_3+k_4)/6
                        dSik[b2, b1] = -dSik[b1, b2]

                # -----------------------------------------------------
                # Step 2: Endogenous premature replacements
                # -----------------------------------------------------
                # Initialise variables related to market share dynamics
                # DSiK contains the change in shares
                dSEik = np.zeros([len(titles['HTTI']), len(titles['HTTI'])])

                # F contains the preferences
                FE = np.ones([len(titles['HTTI']), len(titles['HTTI'])])*0.5

                # Intermediate shares: add the EoL effects before continuing
                # intermediate_shares = data_dt['HEWS'][r, :, 0] + np.sum(dSik, axis=1)

                # Scrappage rate
                SR = divide(np.ones(len(titles['HTTI'])),
                            data['BHTC'][r, :, c4ti["16 Payback time, mean"]]) - data['HETR'][r, :, 0]
                SR = np.where(SR<0.0, 0.0, SR)

                for b1 in range(len(titles['HTTI'])):

                    if not (data_dt['HEWS'][r, b1, 0] > 0.0 and
                            data_dt['HGC2'][r, b1, 0] != 0.0 and
                            data_dt['HGD2'][r, b1, 0] != 0.0 and
                            data_dt['HGC3'][r, b1, 0] != 0.0 and
                            data_dt['HGD3'][r, b1, 0] != 0.0 and
                            SR[b1] > 0.0):
                        continue

                    SE_i = data_dt['HEWS'][r, b1, 0]

                    for b2 in range(b1):

                        if not (data_dt['HEWS'][r, b2, 0] > 0.0 and
                                data_dt['HGC2'][r, b2, 0] != 0.0 and
                                data_dt['HGD2'][r, b2, 0] != 0.0 and
                                data_dt['HGC3'][r, b2, 0] != 0.0 and
                                data_dt['HGD3'][r, b2, 0] != 0.0 and
                                SR[b2] > 0.0):
                            continue

                        SE_k = data_dt['HEWS'][r, b2, 0]

                        # NOTE: Premature replacements are optional for
                        # consumers. It is possible that NO premature
                        # replacements take place

                        # Propagating width of variations in perceived costs
                        dFEik = 1.414 * sqrt((data_dt['HGD3'][r, b1, 0]*data_dt['HGD3'][r, b1, 0] + data_dt['HGD2'][r, b2, 0]*data_dt['HGD2'][r, b2, 0]))
                        dFEki = 1.414 * sqrt((data_dt['HGD2'][r, b1, 0]*data_dt['HGD2'][r, b1, 0] + data_dt['HGD3'][r, b2, 0]*data_dt['HGD3'][r, b2, 0]))

                        # Consumer preference incl. uncertainty
                        FEik = 0.5*(1+np.tanh(1.25*(data_dt['HGC2'][r, b2, 0]-data_dt['HGC3'][r, b1, 0])/dFEik))
                        FEki = 0.5*(1+np.tanh(1.25*(data_dt['HGC2'][r, b1, 0]-data_dt['HGC3'][r, b2, 0])/dFEki))

                        # Preferences are then adjusted for regulations
                        FE[b1, b2] = FEik*(1.0-isReg[r, b1])
                        FE[b2, b1] = FEki*(1.0-isReg[r, b2])

                        #Runge-Kutta market share dynamiccs
                        kE_1 = SE_i*SE_k * (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])
                        kE_2 = (SE_i+dt*kE_1/2)*(SE_k-dt*kE_1/2)* (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])
                        kE_3 = (SE_i+dt*kE_2/2)*(SE_k-dt*kE_2/2) * (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])
                        kE_4 = (SE_i+dt*kE_3)*(SE_k-dt*kE_3) * (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])

                        dSEik[b1, b2] = dt*(kE_1+2*kE_2+2*kE_3+kE_4)/6
                        dSEik[b2, b1] = -dSEik[b1, b2]

                        # TODO: Calculate additional EOL values

                #calculate temportary market shares and temporary capacity from endogenous results
                endo_shares = data_dt['HEWS'][r, :, 0] + np.sum(dSik, axis=1) + np.sum(dSEik, axis=1)
                
                endo_capacity = endo_shares * rhudt[r, np.newaxis]/data['BHTC'][r, :, c4ti["13 Capacity factor mean"]]/1000

                endo_gen = endo_shares * rhudt[r, np.newaxis]

                # -----------------------------------------------------
                # Step 3: Exogenous sales additions
                # -----------------------------------------------------
                # Add in exogenous sales figures. These are blended with
                # endogenous result! Note that it's different from the
                # ExogSales specification!
                Utot = rhudt[r]
                dSk = np.zeros([len(titles['HTTI'])])
                dUk = np.zeros([len(titles['HTTI'])])
                dUkTK = np.zeros([len(titles['HTTI'])])
                dUkREG = np.zeros([len(titles['HTTI'])])

                #Note, as in FTT: H shares are shares of generation, corrections MUST be done in terms of generation. Otherwise, the corrections won't line up with the market shares.


                # Convert exogenous shares to exogenous generation. Exogenous sharess no longer need to add up to 1. Beware removals!
                dUkTK = data['HWSA'][r, :, 0]*Utot/no_it
               
                #Check endogenous shares plus additions for a single time step does not exceed regulated shares
                reg_vs_exog = ((data['HWSA'][r, :, 0]/no_it + endo_shares) > data['HREG'][r, :, 0]) & (data['HREG'][r, :, 0] >= 0.0)
                #Filter capacity additions based on regulated shares
                dUkTK = np.where(reg_vs_exog, 0.0, dUkTK)



                # Correct for regulations due to the stretching effect. This is the difference in generation due only to demand increasing.
                # This will be the difference between generation based on the endogenous generation, and what the endogenous generation would have been
                # if total demand had not grown.

                dUkREG = -(endo_gen - endo_shares*rhudlt[r,np.newaxis])*isReg[r, :].reshape([len(titles['HTTI'])])
                     

                # Sum effect of exogenous sales additions (if any) with
                # effect of regulations
                dUk = dUkREG + dUkTK
                dUtot = np.sum(dUk)

  
                # Calaculate changes to endogenous generation, and use to find new market shares
                # Zero generation will result in zero shares
                # All other capacities will be streched

                data['HEWS'][r, :, 0] = (endo_gen + dUk)/(np.sum(endo_gen)+dUtot)

                if ~np.isclose(np.sum(data['HEWS'][r, :, 0]), 1.0, atol=1e-2):
                    msg = """Sector: {} - Region: {} - Year: {}
                    Sum of market shares do not add to 1.0 (instead: {})
                    """.format(sector, titles['RTI'][r], year, np.sum(data['HEWS'][r, :, 0]))
                    warnings.warn(msg)

                if np.any(data['HEWS'][r, :, 0] < 0.0):
                    msg = """Sector: {} - Region: {} - Year: {}
                    Negative market shares detected! Critical error!
                    """.format(sector, titles['RTI'][r], year)
                    warnings.warn(msg)
#                        t4 = time.time()
#                        print("Share equation takes {}".format(t4-t3))

            ############## Update variables ##################
            # Useful heat by boiler
            data['HEWG'][:, :, 0] = data['HEWS'][:, :, 0] * rhudt[:, 0, 0, np.newaxis]
            # Assuming 'r' is your row index


            # Final energy by boiler
            data['HEWF'][:, :, 0] = divide(data['HEWG'][:, :, 0],
                                             data['BHTC'][:, :, c4ti["9 Conversion efficiency"]])

            # Capacity by boiler
            data['HEWK'][:, :, 0] = divide(data['HEWG'][:, :, 0],
                                              data['BHTC'][:, :, c4ti["13 Capacity factor mean"]])/1000

            # Emissions
            # TODO: Cost titles are wrong
            data['HEWE'][:, :, 0] = data['HEWF'][:, :, 0] * data['BHTC'][:, :, c4ti["15 Emission factor"]]/1e6

            #data['HFPR'][:, :, 0] = copy.deepcopy(data['HFFC'][:, :, 0])

            # Now transform price rates by fuel to price rates by boiler
            #data['HEWP'][:, :, 0] = np.matmul(data['HFFC'][:, :, 0], data['HJET'][0, :, :].T)


            #to match e3me:
            data['HEWI'][:, :, 0] = ((data['HEWK'][:, :, 0] - data_dt['HEWK'][:, :, 0])/dt  \
                                        + data_dt['HEWK'][:, :, 0]*data['HETR'][:, :, 0])


            data['HEWI'][:, :, 0] = np.where(data['HEWI'][:, :, 0] < 0.0,
                                               0.0,
                                               data['HEWI'][:, :, 0])

            # Final energy demand for heating purposes
            data['HJHF'][:, :, 0] = np.matmul(data['HEWF'][:, :, 0], data['HJET'][0, :, :])

            # Final energy demand of the residential sector (incl. non-heat)
            # For the time being, this is calculated as a simply scale-up
            for fuel in range(len(titles['JTI'])):
                if data['HJFC'][r, fuel, 0] > 0.0:
                    data['HJEF'][r, fuel, 0] = data['HJHF'][r, fuel, 0] / data['HJFC'][r, fuel, 0]

            ############## Learning-by-doing ##################

            # Cumulative global learning
            # Using a technological spill-over matrix (HEWB) together with capacity
            # additions (HEWI) we can estimate total global spillover of similar
            # technologies
            bi = np.zeros((len(titles['RTI']),len(titles['HTTI'])))
            for r in range(len(titles['RTI'])):
                bi[r,:] = np.matmul(data['HEWB'][0, :, :],data['HEWI'][r, :, 0])
            dw = np.sum(bi, axis=0)*dt


            # Cumulative capacity incl. learning spill-over effects
            data['HEWW'][0, :, 0] = data_dt['HEWW'][0, :, 0] + dw

            # Copy over the technology cost categories that do not change (all except prices which are updated through learning-by-doing below)
            data['BHTC'] = copy.deepcopy(data_dt['BHTC'])

            # Learning-by-doing effects on investment
            for b in range(len(titles['HTTI'])):

                if data['HEWW'][0, b, 0] > 0.0001:

                    data['BHTC'][:, b, c4ti['1 Inv cost mean (EUR/Kw)']] = (data_dt['BHTC'][:, b, c4ti['1 Inv cost mean (EUR/Kw)']]  \
                                                                             *(1.0 + data['BHTC'][:, b, c4ti['7 Investment LR']] * dw[b]/data['HEWW'][0, b, 0]))
                    data['BHTC'][:, b, c4ti['2 Inv Cost SD']] = (data_dt['BHTC'][:, b, c4ti['2 Inv Cost SD']]  \
                                                                             *(1.0 + data['BHTC'][:, b, c4ti['7 Investment LR']] * dw[b]/data['HEWW'][0, b, 0]))


            #Total investment in new capacity in a year (m 2014 euros):
              #HEWI is the continuous time amount of new capacity built per unit time dI/dt (GW/y)
              #BHTC(:,:,1) are the investment costs (2014Euro/kW)
            data['HWIY'][:,:,0] = data['HWIY'][:,:,0] + data['HEWI'][:,:,0]*dt*data['BHTC'][:,:,0]/data['PRSC14'][:,0,0,np.newaxis]


            # =================================================================
            # Update the time-loop variables
            # =================================================================

            #Calculate levelised cost again
            data = get_lcoh(data, titles)

            #Update time loop variables:
            for var in data_dt.keys():

                data_dt[var] = copy.deepcopy(data[var])


    return data
