# -*- coding: utf-8 -*-
"""

=========================================
Industrial sector module.

Note - functions are missing. Prototype stage.

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
import time

# Third party imports
import pandas as pd
import numpy as np

# Local library imports
from support.divide import divide
from support.econometrics_functions import estimation

# %% lcoh
# -----------------------------------------------------------------------------
# --------------------------- LCOH function -----------------------------------
# -----------------------------------------------------------------------------
def get_lcoih(data, titles):
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

    # Categories for the cost matrix (ICET)
    ctti = {category: index for index, category in enumerate(titles['CTTI'])}

    for r in range(len(titles['RTI'])):
        if data['IHUD'][r, :, 0].sum(axis=0)==0:
            continue

        # Cost matrix
        icet = data['ICET'][r, :, :]

        lt = icet[:, ctti['5 Lifetime (years)']]
        max_lt = int(np.max(lt))
        lt_mat = np.linspace(np.ones(len(titles['ITTI'])), max_lt,
                             num=max_lt, axis=1, endpoint=True)
        lt_max_mat = np.concatenate(int(max_lt)*[lt[:, np.newaxis]+1], axis=1)
        mask = lt_mat < lt_max_mat
        lt_mat = np.where(mask, lt_mat, 0)


        # Capacity factor used in decisions (constant), not actual capacity factor #TODO ask about this
        cf = icet[:, ctti['13 Capacity factor mean'], np.newaxis]

        # Trap for very low CF
        cf[cf<0.000001] = 0.000001

        # Factor to transfer cost components in terms of capacity to generation
#        ones = np.ones([len(titles['ITTI']), 1])
        conv = 1/(cf)/8766 #number of hours in a year

        # Discount rate
        # dr = icet[6]
        dr = icet[:, ctti['8 Discount rate'], np.newaxis]

        # Initialse the levelised cost components
        # Average investment cost
        it = np.ones([len(titles['ITTI']), int(max_lt)])
        it = it * icet[:, ctti['1 Investment cost mean (MEuro per MW)'], np.newaxis] * conv


        # Standard deviation of investment cost
        dit = np.ones([len(titles['ITTI']), int(max_lt)])
        dit = dit * icet[:, ctti['2 Investment cost SD'], np.newaxis] * conv


        # Subsidies
        #st = np.ones([len(titles['ITTI']), int(max_lt)])
        #st = (st * icet[:, ctti['1 Investment cost mean (MEuro per MW)'], np.newaxis]
             # * data['IEWT'][r, :, :] * conv[:, np.newaxis])


        # Average fuel costs 2010Euros/toe
        ft = np.ones([len(titles['ITTI']), int(max_lt)])
        ft = ft * icet[:, ctti['10 Fuel cost mean'], np.newaxis]/11.63/1000000
        ft = np.where(mask, ft, 0)

        # Standard deviation of fuel costs
        dft = np.ones([len(titles['ITTI']), int(max_lt)])
        dft = dft * icet[:, ctti['11 Fuel cost SD'], np.newaxis]/11.63/1000000
        dft = np.where(mask, dft, 0)

        #fuel tax/subsidies
        #fft = np.ones([len(titles['ITTI']), int(max_lt)])
#        fft = ft * data['PG_FUELTAX'][r, :, :]
#        fft = np.where(lt_mask, ft, 0)

        # Average operation & maintenance cost
        omt = np.ones([len(titles['ITTI']), int(max_lt)])
        omt = omt * icet[:, ctti['3 O&M cost mean (Euros/MJ/s/year)'], np.newaxis]* conv/1000000
        omt = np.where(mask, omt, 0)

        # Standard deviation of operation & maintenance cost
        domt = np.ones([len(titles['ITTI']), int(max_lt)])
        domt = domt * icet[:, ctti['4 O&M cost SD'], np.newaxis]* conv/1000000
        domt = np.where(mask, domt, 0)



        # Net present value calculations
        # Discount rate
        denominator = (1+dr)**lt_mat

        # 1-Expenses
        # 1.1-Without policy costs
        npv_expenses1 = (it+ft+omt)/denominator
        # 1.2-With policy costs
        #npv_expenses2 = (it+st+ft+fft+omt-fit)/denominator
        # 1.3-Only policy costs
        #npv_expenses3 = (st+fft-fit)/denominator
        # 2-Utility
        npv_utility = 1/denominator

        # 3-Standard deviation (propagation of error)
        npv_std = np.sqrt(dit**2 + dft**2 + domt**2)/denominator

        # 1-levelised cost variants in $/pkm
        # 1.1-Bare LCOT

        lcoe = np.sum(npv_expenses1, axis=1)/np.sum(npv_utility, axis=1)

        # 1.2-LCOT including policy costs
        #tlcoe = np.sum(npv_expenses2, axis=1)/np.sum(npv_utility, axis=1)#+data['IEFI'][r, :, 0]
        # 1.3 LCOE excluding policy, including co2 price
        #lcoeco2 = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)
        # 1.3-LCOT of policy costs
        # lcoe_pol = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)+data['MEFI'][r, :, 0]
        # Standard deviation of LCOT
        dlcoe = np.sum(npv_std, axis=1)/np.sum(npv_utility, axis=1)

        # LCOE augmented with gamma values, no gamma values yet
        tlcoeg = lcoe+data['IGAM'][r, :, 0]

        # Pass to variables that are stored outside.
        data['IHLC'][r, :, 0] = lcoe            # The real bare LCOT without taxes
        #data['IHLT'][r, :, 0] = lcoeco2           # The real bare LCOE with taxes
        data['IHLG'][r, :, 0] = tlcoeg         # As seen by consumer (generalised cost)
        data['IHLD'][r, :, 0] = dlcoe          # Variation on the LCOT distribution



    return data

#Final energy demand has to match IEA

# %% main function
# -----------------------------------------------------------------------------
# ----------------------------- Main ------------------------------------------
# -----------------------------------------------------------------------------
def solve(data, time_lag, iter_lag, titles, histend, year, domain):#, #specs, converter, coefficients):
    """
    # TODO:
    NB we need to have a loop for industries! This will run for each industry.
    How should I change data?
    How do I ditch the quarterly time loop? Add RK4!



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

    # Categories for the cost matrix (ICET)
    ctti = {category: index for index, category in enumerate(titles['CTTI'])}

    #Get fuel prices from E3ME and add them to the data for this code
    #Initialise everything #TODO

    #Calculate or read in FED
    #Calculate historical emissions
    data = get_lcoih(data, titles)

    # Endogenous calculation takes over from here
    if year > histend['IHUD']:

        # Create a local dictionary for timeloop variables
        # It contains values between timeloop interations in the FTT core
        data_dt = {}

        # First, fill the time loop variables with the their lagged equivalents
        for var in time_lag.keys():

            if var.startswith("I"):

                data_dt[var] = copy.deepcopy(time_lag[var])

        # Create the regulation variable #Regulate UED #no regulations yet
        # isReg = np.zeros([len(titles['RTI']), len(titles['ITTI'])])
        # division = np.zeros([len(titles['RTI']), len(titles['ITTI'])])
        # division = divide((data_dt['IHUD'][:, :, 0] - data['IHRG'][:, :, 0]),
        #                   data_dt['IHRG'][:, :, 0])
        # isReg = 1.0 + np.tanh(2*1.25*division)
        # isReg[data['IHRG'][:, :, 0] == 0.0] = 1.0
        # isReg[data['IHRG'][:, :, 0] == -1.0] = 0.0


        # Factor used to create quarterly data from annual figures
        no_it = 2
        dt = 1 / no_it

        ############## Computing new shares ##################

        #Start the computation of shares
        for t in range(1, no_it+1):

            # Interpolate to prevent staircase profile.
            #Time lagged UED plus change in UED * (no of iterations) * dt

            IHudt = time_lag['IHUD'][:, :, 0].sum(axis=1) + (data['IHUD'][:, :, 0].sum(axis=1) - time_lag['IHUD'][:, :, 0].sum(axis=1)) * t * dt

            for r in range(len(titles['RTI'])):

                if IHudt[r] == 0.0:
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

                    if  not (data_dt['IEWS'][r, b1, 0] > 0.0 and
                             data_dt['IHLG'][r, b1, 0] != 0.0 and
                             data_dt['IHLD'][r, b1, 0] != 0.0):
                        continue

                    #TODO: create market share constraints
                    Gijmax[b1] = np.tanh(1.25*data_dt['IESC'][0, b1, 0] - data_dt['IEWS'][r, b1, 0])/0.1
                    #Gijmin[b1] = np.tanh(1.25*(-mes2_dt[r, b1, 0] + mews_dt[r, b1, 0])/0.1)



                    S_i = data_dt['IEWS'][r, b1, 0]


                    for b2 in range(b1):

                        if  not (data_dt['IEWS'][r, b2, 0] > 0.0 and
                                 data_dt['IHLG'][r, b2, 0] != 0.0 and
                                 data_dt['IHLD'][r, b2, 0] != 0.0):
                            continue

                        S_k = data_dt['IEWS'][r,b2, 0]
                        Aik = data['IHWA'][0,b1 , b2]
                        Aki = data['IHWA'][0,b2, b1]

                        # Propagating width of variations in perceived costs
                        dFik = sqrt(2) * sqrt((data_dt['IHLD'][r, b1, 0]*data_dt['IHLD'][r, b1, 0] + data_dt['IHLD'][r, b2, 0]*data_dt['IHLD'][r, b2, 0]))

                        # Consumer preference incl. uncertainty
                        Fik = 0.5*(1+np.tanh(1.25*(data_dt['IHLG'][r, b2, 0]-data_dt['IHLG'][r, b1, 0])/dFik))

                        # Preferences are then adjusted for regulations
                        F[b1, b2] = Fik#*(1.0-isReg[r, b1]) * (1.0 - isReg[r, b2]) + isReg[r, b2]*(1.0-isReg[r, b1]) + 0.5*(isReg[r, b1]*isReg[r, b2])
                        F[b2, b1] = (1.0-Fik)#*(1.0-isReg[r, b2]) * (1.0 - isReg[r, b1]) + isReg[r, b1]*(1.0-isReg[r, b2]) + 0.5*(isReg[r, b2]*isReg[r, b1])


                        #Runge-Kutta market share dynamiccs
                        k_1 = S_i*S_k * (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])
                        k_2 = (S_i+dt*k_1/2)*S_k * (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])
                        k_3 = (S_i+dt*k_2/2)*S_k * (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])
                        k_4 = (S_i+dt*k_3)*S_k * (Aik*F[b1, b2]*Gijmax[b1] - Aki*F[b2, b1]*Gijmax[b2])

                        #This method currently applies RK4 to the shares, but all other components of the equation are calculated for the overall time step
                        #We must assume the the LCOE does not change significantly in a time step dt, so we can focus on the shares.

                        dSik[b1, b2] = dt*(k_1+2*k_2+2*k_3+k_4)/6
                        dSik[b2, b1] = -dSik[b1, b2]

                        #dSik[b1, b2] = S_i*S_k* (Aik*F[b1,b2]*Gijmax[b1] - Aki*F[b2,b1]*Gijmax[b2])*dt
                        #dSik[b2, b1] = -dSik[b1, b2]


                    # -----------------------------------------------------
                    # Step 3: Exogenous sales additions
                    # -----------------------------------------------------
                    # Add in exogenous sales figures. These are blended with endogenous result!

                    Utot = IHudt[r] #This is UED interpolated into a straight line from the actual data


#
                    # New market shares
                    # heck that market shares sum to 1
#                        print(np.sum(dSik, axis=1))
                    data['IEWS'][r, :, 0] = data_dt['IEWS'][r, :, 0] + np.sum(dSik, axis=1)

                    if ~np.isclose(np.sum(data['IEWS'][r, :, 0]), 1.0, atol=1e-5):
                        msg = """Sector: {} - Region: {} - Year: {}
                        Sum of market shares do not add to 1.0 (instead: {})
                        """.format(sector, titles['RTI'][r], year, np.sum(data['IEWS'][r, :, 0]))
                        warnings.warn(msg)

                    if np.any(data['IEWS'][r, :, 0] < 0.0):
                        msg = """Sector: {} - Region: {} - Year: {}
                        Negative market shares detected! Critical error!
                        """.format(sector, titles['RTI'][r], year)
                        warnings.warn(msg)




            # =============================================================
            #  Update variables
            # =============================================================

            #TODO: what else needs to go here?

            #Useful heat by technology, calculate based on new market shares #Regional totals
            data['IHUD'][:, :, 0] = data['IEWS'][:, :, 0]* IHudt[:, np.newaxis]

            #Update emissions
            #IHWE is the global average emissions per unit of UED (GWh). IHWE has units of kt of CO2/GWh
            for r in range(len(titles['RTI'])):
                data['IEWE'][r, :, 0] = data['IHUD'][r, :, 0] * data['IHWE'][0, :, 0]


            #Final energy by technology
            data['IHFD'][:, :, 0] = np.where(data['ICET'][:, :, ctti["9 Conversion efficiency"]] !=0.0,
                                             divide(data['IHUD'][:, :, 0],
                                                    data['ICET'][:, :, ctti["9 Conversion efficiency"]]),
                                            0.0)



            #Estimate capacities in terms of MW IEWK = IHUD/cf/8766

            #Estimate IEWI - yearly capacity additions IEWK-IEWK_lagged, only take positive values
            #add number of devices replaced due to breakdowns = IEWK_lagged/lifetime

            #Read in IEWW global (EU) cumulative capacity
            #Calculate historical capcatiy = UED/cf, extrapolate back to 1950
            #calulate cumulative amounts


            # =============================================================
            # Learning-by-doing #TODO This needs to be based on UED
            # =============================================================

            # Cumulative global learning
            # Using a technological spill-over matrix (IEWB spillover matrix) together with capacity
            # additions (IEWI Capacity additions) we can estimate total global spillover of similar
            # techicals

            #add number of devices replaced due to breakdowns = IEWK_lagged/lifetime to yearly capacity additions
            #note some values of IEWI negative

            data["IEWI"][:, :, 0] = data_dt['IEWI'][:, :, 0] + np.where(data['ICET'][:, :, ctti['5 Lifetime (years)']] !=0.0,
                                                                        time_lag['IEWK'][:, :, 0]/data['ICET'][:, :, ctti['5 Lifetime (years)']],
                                                                        0.0)


            bi = np.matmul(data['IEWI'][:, :, 0], data['IHWB'][0, :, :])
            dw = np.sum(bi, axis=0)*dt

            # # Cumulative capacity incl. learning spill-over effects
            data["IEWW"][0, :, 0] = data_dt['IEWW'][0, :, 0] + dw
            #
            # # Copy over the technology cost categories that do not change (all except prices which are updated through learning-by-doing below)
            data['ICET'] = copy.deepcopy(data_dt['ICET'])
            #
            # # Learning-by-doing effects on investment
            for tech in range(len(titles['ITTI'])):

                if data['IEWW'][0, tech, 0] > 0.1:

                    data['ICET'][:, tech, ctti['1 Investment cost mean (MEuro per MW)']] = data_dt['ICET'][:, tech, ctti['1 Investment cost mean (MEuro per MW)']] * \
                                                                           (1.0 + data['ICET'][:, tech, ctti['15 Learning exponent']] * dw[tech]/data['IEWW'][0, tech, 0])

            # =================================================================
            # Update the time-loop variables
            # =================================================================

            #Calculate levelised cost again
            data = get_lcoih(data, titles)

            #Update time loop variables:
            for var in data_dt.keys():

                if var.startswith("I"):

                    data_dt[var] = copy.deepcopy(data[var])


    return data
