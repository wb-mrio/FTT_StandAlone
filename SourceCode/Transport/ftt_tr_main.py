# -*- coding: utf-8 -*-
"""
=========================================
ftt_tr_main.py
=========================================
Passenger road transport FTT module.


This is the main file for FTT: Transport, which models technological
diffusion of passenger vehicle types due to simulated consumer decision making.
Consumers compare the log of the **levelised costs**, which leads to changes in the
market shares of different technologies.

The outputs of this module include sales, fuel use, and emissions.

Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Element-wise divide which replaces divide-by-zeros with zeros

Functions included:
    - solve
        Main solution function for the module
    - get_lcot
        Calculate levelised cost of transport
    - get_sales
        Calculate new sales/additions in FTT-Transport 
        
"""

# Standard library imports
from math import sqrt
import copy
import warnings

# Third party imports
import numpy as np

# Local library imports
from SourceCode.support.divide import divide
from SourceCode.Transport.ftt_tr_lcot import get_lcot
from SourceCode.ftt_core.ftt_sales_or_investments import get_sales
from SourceCode.Transport.ftt_tr_survival import survival_function, add_new_cars_age_matrix


# %% Fleet size - under development
# -----------------------------------------------------------------------------
# ----------------- Gompertz equation for fleet size --------------------------
# -----------------------------------------------------------------------------
# def fleet_size(data, titles):
#
#     return print("Hello")




# %% main function
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
        Model variables in previous year
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
    # Categories for the cost matrix (BTTC)
    c3ti = {category: index for index, category in enumerate(titles['C3TI'])}
    jti = {category: index for index, category in enumerate(titles['JTI'])}

    fuelvars = ['FR_1', 'FR_2', 'FR_3', 'FR_4', 'FR_5', 'FR_6',
                'FR_7', 'FR_8', 'FR_9', 'FR_10', 'FR_11', 'FR_12']

    sector = "tr_road_pass"
    sector_index = 0
    sector_index = 15 #titles['FUTI'].index('16 Road Transport')

    # Store fuel prices and convert to $2013/toe
    # It's actually in current$/toe
    # TODO: Temporary deflator values
    data['TE3P'][:, jti["5 Middle distillates"], 0] = iter_lag['PFRM'][:, sector_index, 0] / 1.33
    data['TE3P'][:, jti["7 Natural gas"], 0] = iter_lag['PFRG'][:, sector_index, 0] / 1.33
    data['TE3P'][:, jti["8 Electricity"], 0] = iter_lag['PFRE'][:, sector_index, 0] / 1.33
    data['TE3P'][:, jti["11 Biofuels"], 0] = iter_lag['PFRB'][:, sector_index, 0] / 1.33
#    data['TE3P'][:, "12 Hydrogen", 0] = data['PFRE'][:, sector_index, 0] * 2.0

    if year == 2012:
        start_i_cost = np.zeros([len(titles['RTI']), len(titles['VTTI']),1])
        for veh in range(len(titles['VTTI'])):
            if 17 < veh < 24:
                # Starting EV/PHEV cost (without battery)
                start_i_cost[:,veh,0] = (data['BTTC'][:, veh, c3ti['1 Prices cars (USD/veh)']]
                                         / data['BTTC'][:, veh, c3ti['20 Markup factor']]
                                         - data['BTTC'][:, veh, c3ti['18 Battery cap (kWh)']]
                                         * data['BTTC'][:, veh, c3ti['19 Battery cost ($/kWh)']]
                                         - data['BTTC'][:, veh, c3ti['1 Prices cars (USD/veh)']] * 0.15)
            else:
                start_i_cost[:,veh,0] = 0
        # TEVC is 'Start_ICost' in the Fortran model
        data["TEVC"] = start_i_cost
    elif year > 2012:
        # Copy over TEVC values
        data['TEVC'] = np.copy(time_lag['TEVC'] )


    for r in range(len(titles['RTI'])):
        # %% Initialise
        # Up to the last year of historical market share data
        if year <= data["TDA1"][r, 0, 0]:
        
        
            # Correction to market shares
            # Sometimes historical market shares do not add up to 1.0
            if (~np.isclose(np.sum(data['TEWS'][r, :, 0]), 1.0, atol=1e-9)
                    and np.sum(data['TEWS'][r, :, 0]) > 0.0):
                data['TEWS'][r, :, 0] = np.divide(data['TEWS'][r, :, 0],
                                                   np.sum(data['TEWS'][r, :, 0]))

            # Computes initial values for the capacity factor, numbers of
            # vehicles by technology and distance driven
    
            # "Capacities", defined as 1000 vehicles
            data['TEWK'][:, :, 0] = data['TEWS'][:, :, 0] * data['RFLT'][:, 0, 0, np.newaxis]
    
            # "Generation", defined as total mln km driven
            data['TEWG'][:, :, 0] = data['TEWK'][:, :, 0] * data['RVKM'][:, 0, 0, np.newaxis] * 1e-3

            # "Emissions", Factor 1.2 approx fleet efficiency factor, corrected later with CO2_corr
            data['TEWE'][:, :, 0] = data['TEWG'][:, :, 0] * data['BTTC'][:, :, c3ti['14 CO2Emissions']]/1e6*1.2
    
        

        if year == data["TDA1"][r, 0, 0]: 
            # Define starting battery capacity
            start_bat_cap = np.copy(data["TEWW"])
            for veh in range(len(titles['VTTI'])):
                if (veh < 18) or (veh > 23):
                    # Set starting cumulative battery capacities to 0 for ICE vehicles
                    start_bat_cap[0,veh,0] = 0
            # TWWB is 'StartBatCap' in the FORTRAN model
            data["TWWB"] = start_bat_cap

            # Save initial cost matrix (BTCLi from FORTRAN model)
            data["BTCI"] = np.copy(data["BTTC"])

            # This corrects for higher emissions/fuel use at older age depending how fast the fleet has grown
            CO2_corr = np.ones(len(titles['RTI']))

            # Fuel use
            # Compute fuel use as distance driven times energy use, corrected by the biofuel mandate.
            emis_corr = np.zeros([len(titles['RTI']), len(titles['VTTI'])])
            fuel_converter = np.zeros([len(titles['VTTI']), len(titles['JTI'])])
            fuel_converter = data['TJET'][0, :, :]

        
            if data['RFLT'][r, 0, 0] > 0.0:
                CO2_corr[r] = (data['TESH'][r, :, 0] * data['TESF'][r, :, 0]* \
                         data['TETH'][r, :, 0]).sum() / (data['TESH'][r, :, 0] * data['TESF'][r, :, 0]).sum()

            for fuel in range(len(titles['JTI'])):

                for veh in range(len(titles['VTTI'])):

                    if titles['JTI'][fuel] == '5 Middle distillates' and data['TJET'][0, veh, fuel] == 1:  # Middle distillates

                        # Mix with biofuels/hydrogen if there's a biofuel mandate or hydrogen mandate
                        fuel_converter[veh, fuel] = data['TJET'][0, veh, fuel] * (1.0 - data['RBFM'][r, 0, 0])

                        # Emission correction factor
                        emis_corr[r, veh] = 1.0 - data['RBFM'][r, 0, 0]

                    elif titles['JTI'][fuel] == '11 Biofuels'  and data['TJET'][0, veh, fuel] == 1:

                        fuel_converter[veh, fuel] = data['TJET'][0, veh, fuel] * data['RBFM'][r, 0, 0]

            # Calculate fuel use - passenger car only! Therefore this will
            # differ from E3ME results
            # TEWG:                          mkm driven
            # Convert energy unit (1/41.868) ktoe/TJ
            # Energy demand (BTTC)           MJ/km

            data['TJEF'][r, :, 0] = (np.matmul(np.transpose(fuel_converter), data['TEWG'][r, :, 0]*\
                                    data['BTTC'][r, :, c3ti['9 energy use (MJ/km)']]*CO2_corr[r]/41.868))

            # "Emissions"
            data['TEWE'][r, :, 0] = (data['TEWG'][r, :, 0] * data['BTTC'][r, :, c3ti['14 CO2Emissions']]
                                     * CO2_corr[r] * emis_corr[r,:]/1e6)
    
    # Call the survival function routine, updating scrappage and age matrix:
    if year <= np.max(data["TDA1"][:, 0, 0]):
        data = survival_function(data, time_lag, histend, year, titles)
        

    # Calculate the LCOT for each vehicle type.
    # Call the function
    data = get_lcot(data, titles, year)

    # %% Simulation of stock and energy specs

    if year > np.min(data["TDA1"][:, 0, 0]): 
        # Regions have different start dates (TDA1); regions with historical data are later skipped

        # Create a local dictionary for timeloop variables
        # It contains values between timeloop interations in the FTT core
        data_dt = {}

        # First, fill the time loop variables with the their lagged equivalents
        for var in time_lag.keys():

            data_dt[var] = np.copy(time_lag[var])

        data_dt['TWIY'] = np.zeros([len(titles['RTI']), len(titles['VTTI']), 1])

        # Create the regulation variable
        division = divide((time_lag['TEWK'][:, :, 0] - data['TREG'][:, :, 0]), data['TREG'][:, :, 0]) # 0 when dividing by 0
        isReg = 0.5 + 0.5*np.tanh(1.5 + 10 * division)
        isReg[data['TREG'][:, :, 0] == 0.0] = 1.0
        isReg[data['TREG'][:, :, 0] == -1.0] = 0.0

        # Factor used to create quarterly data from annual figures
        no_it = int(data['noit'][0, 0, 0])
        dt = 1 / float(no_it)

        ############## Computing new shares ##################

        # Start the computation of shares
        for t in range(1, no_it + 1):
            
            # Both rvkm and RFLT are exogenous at the moment
            # Interpolate to prevent staircase profile.
            rvkmt = time_lag['RVKM'][:, 0, 0] + (data['RVKM'][:, 0, 0] - time_lag['RVKM'][:, 0, 0]) * t * dt
            rfllt = time_lag['RFLT'][:, 0, 0] + (data['RFLT'][:, 0, 0] - time_lag['RFLT'][:, 0, 0]) * (t-1) * dt
            rfltt = time_lag['RFLT'][:, 0, 0] + (data['RFLT'][:, 0, 0] - time_lag['RFLT'][:, 0, 0]) * t * dt

            for r in range(len(titles['RTI'])):
                # Skip regions for which more recent data is available
                if data['TDA1'][r, 0, 0] >= year:
                    continue
                
                if rfltt[r] == 0.0:
                    continue
                

                ############################ FTT ##################################
                # Initialise variables related to market share dynamics
                # DSiK contains the change in shares
                dSik = np.zeros([len(titles['VTTI']), len(titles['VTTI'])])

                # F contains the preferences
                F = np.ones([len(titles['VTTI']), len(titles['VTTI'])])*0.5


                # TODO: Check Specs dimensions
                #if np.any(specs[sector][r, :] == 1):  # FTT Specification

                for v1 in range(len(titles['VTTI'])):
                    
                    # Skip technologies with zero market share or zero costs
                    if not (data_dt['TEWS'][r, v1, 0] > 0.0 and
                            data_dt['TELC'][r, v1, 0] != 0.0 and
                            data_dt['TLCD'][r, v1, 0] != 0.0):
                        continue

                    S_veh_i = data_dt['TEWS'][r, v1, 0]


                    for v2 in range(v1):
                        
                        # Skip technologies with zero market share or zero costs
                        if not (data_dt['TEWS'][r, v2, 0] > 0.0 and
                                data_dt['TELC'][r, v2, 0] != 0.0 and
                                data_dt['TLCD'][r, v2, 0] != 0.0):
                            continue

                        S_veh_k = data_dt['TEWS'][r, v2, 0]
                        Aik = data['TEWA'][0, v1 , v2] / data['BTTC'][r, v1, c3ti['17 Turnover rate']]
                        Aki = data['TEWA'][0, v2 , v1] / data['BTTC'][r, v2, c3ti['17 Turnover rate']]

                        # Propagating width of variations in perceived costs
                        dFik = 1.414 * sqrt((data_dt['TLCD'][r, v1, 0] * data_dt['TLCD'][r, v1, 0] 
                                               + data_dt['TLCD'][r, v2, 0] * data_dt['TLCD'][r, v2, 0]))

                        # Consumer preference incl. uncertainty
                        Fik = 0.5 * (1 + np.tanh(1.25 * (data_dt['TELC'][r, v2, 0] 
                                                         - data_dt['TELC'][r, v1, 0]) / dFik))
                        # Preferences are then adjusted for regulations
                        F[v1, v2] = (Fik * (1.0 - isReg[r, v1]) * (1.0 - isReg[r, v2]) + isReg[r, v2] 
                                     * (1.0 - isReg[r, v1]) + 0.5 * (isReg[r, v1] * isReg[r, v2]))
                        F[v2, v1] = ((1.0 - Fik) * (1.0 - isReg[r, v2]) * (1.0 - isReg[r, v1]) + isReg[r, v1] 
                                     * (1.0-isReg[r, v2]) + 0.5 * (isReg[r, v2] * isReg[r, v1]))

                        # Runge-Kutta market share dynamiccs
                        k_1 = S_veh_i*S_veh_k* (Aik*F[v1,v2] - Aki*F[v2,v1])
                        k_2 = (S_veh_i+dt*k_1/2)*(S_veh_k-dt*k_1/2)* (Aik*F[v1,v2] - Aki*F[v2,v1])
                        k_3 = (S_veh_i+dt*k_2/2)*(S_veh_k-dt*k_2/2) * (Aik*F[v1,v2] - Aki*F[v2,v1])
                        k_4 = (S_veh_i+dt*k_3)*(S_veh_k-dt*k_3) * (Aik*F[v1,v2] - Aki*F[v2,v1])

                        # Market share dynamics
                        #dSik[v1, v2] = S_veh_i*S_veh_k* (Aik*F[v1,v2] - Aki*F[v2,v1])*dt
                        dSik[v1, v2] = dt*(k_1+2*k_2+2*k_3+k_4)/6
                        dSik[v2, v1] = -dSik[v1, v2]

                # Calculate temporary market shares and temporary capacity from endogenous results
                endo_shares = data_dt['TEWS'][r, :, 0] + np.sum(dSik, axis=1) 
                endo_capacity = endo_shares * rfltt[r, np.newaxis]

                Utot = rfltt[r]
                dUkTK = np.zeros([len(titles['VTTI'])])
                dUkREG = np.zeros([len(titles['VTTI'])])
                TWSA_scalar = 1.0

                # Check that exogenous sales additions aren't too large
                # As a proxy it can't be greater than 80% of the fleet size
                # divided by 13 (the average lifetime of vehicles)
                if (data['TWSA'][r, :, 0].sum() > 0.8 * rfltt[r] / 13):

                    TWSA_scalar = data['TWSA'][r, :, 0].sum() / (0.8 * rfltt[r] / 13)
                # Check endogenous capacity plus additions for a single time step does not exceed regulated capacity.
                reg_vs_exog = ((data['TWSA'][r, :, 0]/TWSA_scalar/no_it + endo_capacity) 
                               > data['TREG'][r, :, 0]) & (data['TREG'][r, :, 0] >= 0.0)

                # TWSA is yearly capacity additions. We need to split it up based on the number of time steps, and also scale it if necessary.
                dUkTK =  np.where(reg_vs_exog, 0.0, data['TWSA'][r, :, 0]/TWSA_scalar/no_it)

                # Correct for regulations due to the stretching effect. This is the difference in capacity due only to rflt increasing.
                # This is the difference between capacity based on the endogenous capacity, and what the endogenous capacity would have been
                # if rflt (i.e. total demand) had not grown.

                dUkREG = -(endo_capacity - endo_shares * rfllt[r,np.newaxis]) * isReg[r, :].reshape([len(titles['VTTI'])])
                           
                # Sum effect of exogenous sales additions (if any) with effect of regulations. 
                dUk = dUkTK + dUkREG
                dUtot = np.sum(dUk)

                # Calaculate changes to endogenous capacity, and use to find new market shares
                # Zero capacity will result in zero shares
                # All other capacities will be streched
            
                data['TEWS'][r, :, 0] = (endo_capacity + dUk)/(np.sum(endo_capacity)+dUtot)

                # Check shares sum to 1 
                if ~np.isclose(np.sum(data['TEWS'][r, :, 0]), 1.0, atol=1e-3):
                    msg = f"""Sector: {sector} - Region: {titles['RTI'][r]} - Year: {year}
                    Sum of market shares do not add to 1.0 (instead: {np.sum(data['TEWS'][r, :, 0])})
                    """
                    warnings.warn(msg)

                if np.any(data['TEWS'][r, :, 0] < 0.0):
                    msg = f"""Sector: {sector} - Region: {titles['RTI'][r]} - Year: {year}
                    Negative market shares detected! Critical error!
                    """
                    warnings.warn(msg)


            ############## Update variables ##################

            # Update demand for driving (in km/ veh/ y) - exogenous atm
            #data['TEWL'][:, :, 0] = rvkmt[:, 0, 0]
            # Vehicle composition
            data['TEWK'][:, :, 0] = data['TEWS'][:, :, 0] * rfltt[:, np.newaxis]
            # Total distance driven per vehicle type
            data['TEWG'][:, :, 0] = data['TEWK'][:, :, 0] * rvkmt[:, np.newaxis] * 1e-3

            
            # New additions (TEWI)
            data["TEWI"], tewi_t = get_sales(
                data["TEWK"], data_dt["TEWK"], time_lag["TEWK"], data["TEWS"], 
                data_dt["TEWS"], data["TEWI"], data['BTTC'][:, :, c3ti['8 lifetime']], dt)
            
           

            # Fuel use
            # Compute fuel use as distance driven times energy use, corrected by the biofuel mandate.
            CO2_corr = np.ones(len(titles['RTI']))
            emis_corr = np.zeros([len(titles['RTI']), len(titles['VTTI'])])
            fuel_converter = np.zeros([len(titles['VTTI']), len(titles['JTI'])])
            fuel_converter = data['TJET'][0, :, :]

            for r in range(len(titles['RTI'])):
                if data['RFLT'][r, 0, 0] > 0.0:
                    CO2_corr[r] = (data['TESH'][r, :, 0]*data['TESF'][r, :, 0]* \
                             data['TETH'][r, :, 0]).sum()/(data['TESH'][r, :, 0]*data['TESF'][r, :, 0]).sum()

                for fuel in range(len(titles['JTI'])):

                    for veh in range(len(titles['VTTI'])):

                        if titles['JTI'][fuel] == '5 Middle distillates' and data['TJET'][0, veh, fuel] ==1:  # Middle distillates

                            # Mix with biofuels/hydrogen if there's a biofuel mandate or hydrogen mandate
                            fuel_converter[veh, fuel] = data['TJET'][0, veh, fuel] * (1.0 - data['RBFM'][r, 0, 0])

                            # Emission correction factor
                            emis_corr[r, veh] = 1.0 - data['RBFM'][r, 0, 0]

                        elif titles['JTI'][fuel] == '11 Biofuels'  and data['TJET'][0, veh, fuel] == 1:

                            fuel_converter[veh, fuel] = data['TJET'][0, veh, fuel] * data['RBFM'][r, 0, 0]

                # Calculate fuel use - passenger car only! Therefore this will
                # differ from E3ME results
                # TEWG:                          mkm driven
                # Convert energy unit (1/41.868) ktoe/TJ
                # Energy demand (BBTC)           MJ/km

                # Fuel use
                data['TJEF'][r, :, 0] = (np.matmul(np.transpose(fuel_converter), data['TEWG'][r, :, 0]
                                        * data['BTTC'][r, :, c3ti['9 energy use (MJ/km)']] 
                                        * CO2_corr[r] / 41.868))

                # Emissions
                data['TEWE'][r, :, 0] = (data['TEWG'][r, :, 0] * data['BTTC'][r, :, c3ti['14 CO2Emissions']]
                                         * CO2_corr[r] * emis_corr[r,:] / 1e6)

            ############## Learning-by-doing ##################

            # Cumulative global learning
            # Using a technological spill-over matrix (TEWB) together with capacity
            # additions (TEWI) we can estimate total global spillover of similar
            # vehicles
            # bi = np.matmul(data['TEWI'][:, :, 0], data['TEWB'][0, :, :])
            # dw = np.sum(bi, axis=0)*dt
                
            # New battery additions (MWh) = new sales (1000 vehicles) * average battery capacity (kWh)  
            new_bat = np.zeros([len(titles['RTI']), len(titles['VTTI']),1])
            new_bat[:, :, 0] = tewi_t[:, :, 0] * data["BTTC"][:, :, c3ti["18 Battery cap (kWh)"]]  
            
            # Cumulative investment for learning cost reductions
            bi = np.zeros((len(titles['RTI']), len(titles['VTTI'])))
            for r in range(len(titles['RTI'])):
                # Investment spillover
                bi[r, :] = np.matmul(data['TEWB'][0, :, :], tewi_t[r, :, 0])
            
            # Total new investment
            dw = np.sum(bi, axis=0)
            # Total new battery investment (in MWh)
            dwev = np.sum(new_bat, axis=0)    

            # Copy over TWWB values
            data['TWWB'] = np.copy(time_lag['TWWB'])

            # Cumulative capacity for batteries first
            data['TEWW'][0, :, 0] = data_dt['TEWW'][0, :, 0] + dwev[:, 0]
            bat_cap = np.copy(data["TEWW"])

            # Cumulative capacity for ICE vehicles
            for veh in range(len(titles['VTTI'])):
                if (veh < 18) or (veh > 23):
                    data['TEWW'][0, veh, 0] = data_dt['TEWW'][0, veh, 0] + dw[veh]
                    # Make sure bat_cap for ICE vehicles is 0
                    bat_cap[0, veh, 0] = 0

            # Copy over the technology cost categories that do not change 
            # (all except prices which are updated through learning-by-doing below)
            data['BTTC'] = np.copy(data_dt['BTTC'])
            # Copy over the initial cost matrix
            data["BTCI"] = np.copy(data_dt['BTCI'])


            # Battery learning
            for veh in range(len(titles['VTTI'])):
                if 17 < veh < 24:
                    # Battery cost as a result of learning
                    # Battery cost = energy density over time*rare metal price trend over time
                    data["BTTC"][:, veh, c3ti['19 Battery cost ($/kWh)']] = (
                        (data["BTTC"][:, veh, c3ti['22 Energy density']] ** (year - 2022)) 
                        * (data["BTTC"][:, veh, c3ti['21 Rare metal price']] ** (year - 2022)) 
                        * data['BTCI'][:, veh, c3ti['19 Battery cost ($/kWh)']] 
                        * (np.sum(bat_cap, axis=1) / np.sum(data["TWWB"], axis=1))
                        ** data["BTTC"][:, veh, c3ti['16 Learning exponent']])                 
            
            # Save battery cost
            data["TEBC"] = np.zeros([len(titles['RTI']), len(titles['VTTI']),1])
            data["TEBC"][:, :, 0] = data["BTTC"][:, :, c3ti['19 Battery cost ($/kWh)']]
            
            # Initialise variable for indirect EV/PHEV costs
            id_cost = np.zeros([len(titles['RTI']), len(titles['VTTI']),1])
            # Initialise variable for cost of EV/PHEV - battery
            i_cost = np.zeros([len(titles['RTI']), len(titles['VTTI']),1])
            
            # Learning-by-doing effects on investment
            for veh in range(len(titles['VTTI'])):
                if data['TEWW'][0, veh, 0] > 0.1:
                    # Learning on indirect costs (only relevant for EVs and PHEVs)
                    id_cost[:, veh, 0] = (data['BTCI'][:, veh, c3ti['1 Prices cars (USD/veh)']] 
                               * 0.15 * 0.993**(year - 2022))
                    # Learning on the EV/PHEV (seperate from battery)
                    i_cost[:, veh, 0] = (data["TEVC"][:, veh, 0] 
                                        * ((np.sum(bat_cap, axis=1) / np.sum(data["TWWB"], axis=1)) 
                                        ** (data["BTTC"][:, veh, c3ti['16 Learning exponent']]/2))
                                        )
                    
                    # Calculate new costs (seperate treatments for ICE vehicles and EVs/PHEVs)
                    if 17 < veh < 24:
                        # EVs and PHEVs HERE     
                        # Cost (excluding the cost of battery) + Updated cost of battery
                        # + updated indirect cost) * Markup factor
                        data['BTTC'][:, veh, c3ti['1 Prices cars (USD/veh)']] =  \
                                ((i_cost[:,veh,0] + (data["BTTC"][:, veh, c3ti['19 Battery cost ($/kWh)']] 
                                 * data["BTTC"][:, veh, c3ti['18 Battery cap (kWh)']]) + id_cost[:, veh, 0]) 
                                 * data['BTTC'][:, veh, c3ti['20 Markup factor']])
                    else:
                        # ICE HERE
                        data['BTTC'][:, veh, c3ti['1 Prices cars (USD/veh)']] = \
                            data_dt['BTTC'][:, veh, c3ti['1 Prices cars (USD/veh)']] \
                            * (1.0 + data['BTTC'][:, veh, c3ti['16 Learning exponent']] \
                            * dw[veh] / data['TEWW'][0, veh, 0])

            # Investment in terms of car purchases:
            for r in range(len(titles['RTI'])):

                data['TWIY'][r, :, 0] = (data_dt['TWIY'][r, :, 0] + data['TEWI'][r, :, 0] * dt 
                                        * data['BTTC'][r, :, c3ti['1 Prices cars (USD/veh)']] / 1.33
                                        )


            # =================================================================
            # Update the time-loop variables
            # =================================================================

            # Calculate levelised cost again
            data = get_lcot(data, titles, year)

            # Update time loop variables:
            for var in data_dt.keys():

                data_dt[var] = np.copy(data[var])

        # Call the survival function routine
        data = survival_function(data, time_lag, histend, year, titles)
        if year == 2050:
            print(f"Total electric cars in 2050: {np.sum(data['TEWK'][:, 18, 0] + data['TEWK'][:, 19, 0] + data['TEWK'][:, 20, 0])}")
        
    return data
