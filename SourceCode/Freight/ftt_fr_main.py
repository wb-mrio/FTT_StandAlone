# -*- coding: utf-8 -*-
"""
============================================================
ftt_fr_main.py
============================================================
Freight transport FTT module.

This is the main file for FTT: Freight, which models technological
diffusion of freight vehicle types due to simulated consumer decision making.
Consumers compare the **levelised cost of freight**, which leads to changes 
in the market shares of different technologies.

The outputs of this module include market shares, fuel use, and emissions.

Local library imports:

    FTT: Freight functions:
    - `get_lcof <ftt_fr_lcof.html>`__
        Levelised cost calculation

    Support functions:
    - `divide <divide.html>`__
        Element-wise divide which replaces divide-by-zeros with zeros

Functions included:
    - solve
        Main solution function for the module
    - get_lcof
        Calculate levelised cost of freight

"""

# Standard library imports
import warnings

# Third party imports
import numpy as np

# Local library imports
from SourceCode.Freight.ftt_fr_lcof import get_lcof
from SourceCode.Freight.ftt_fr_shares import shares, implement_shares_policies
from SourceCode.support.divide import divide
from SourceCode.Freight.ftt_fr_sales import get_sales

# %% main function
# -----------------------------------------------------------------------------
# ----------------------------- Main ------------------------------------------
# -----------------------------------------------------------------------------
def solve(data, time_lag, titles, histend, year, domain):
    """
    Main solution function for the module.

    This function simulates investor decision making in the freight sector.
    Levelised costs (from the get_lcof function) are taken and market shares
    for each vehicle type are simulated to ensure demand is met.

    Parameters
    -----------
    data: dictionary of NumPy arrays
        Model variables for given year of solution
    time_lag: type
        Model variables from the previous year
    titles: dictionary of lists
        Dictionary containing all title classification
    histend: dict of integers
        Final year of histrorical data by variable
    year: int
        Curernt/active year of solution

    Returns
    ----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution

    """

    # Categories for the cost matrix
    c6ti = {category: index for index, category in enumerate(titles['C6TI'])}

    sector = 'freight'

    # Factor used to create intermediate data from annual figures
    no_it = int(data['noit'][0, 0, 0])
    dt = 1 / float(no_it)

    # Creating variables
    # Technology to fuel user conversion matrix
    zjet = np.copy(data['ZJET'][0, :, :])
    # Initialise the emission correction factor
    emis_corr = np.zeros([len(titles['RTI']), len(titles['FTTI'])])
    n_veh_classes = len(titles['FSTI'])
    
    def sum_over_classes(var):
        output = np.stack([
                    np.sum(var[:, veh_class::n_veh_classes, :], axis=1)
                    for veh_class in range(n_veh_classes)],
                    axis=1)
        return output

    # Initialise up to the last year of historical data
    if year <= histend["RFLZ"]:
        
        summed_zews = sum_over_classes(data['ZEWS'])
        for r in range(len(titles['RTI'])):
            # Correction to market shares for each vehicle class
            # Sometimes historical market shares do not add up to 1.0
            for veh_class in range(n_veh_classes):
                if (~np.isclose(summed_zews[r, veh_class, 0], 1.0, atol=1e-9)
                    and summed_zews[r, veh_class, 0] > 0.0):
                        data['ZEWS'][r, :, 0] = np.divide(data['ZEWS'][r, veh_class::n_veh_classes, 0],
                                                    summed_zews[r, veh_class, 0])
            
        
        # Calculate number of vehicles per technology. First reshape rflz into right format
        rflz_reshaped = np.tile(data['RFLZ'], (1, data['ZEWS'].shape[1] // data['RFLZ'].shape[1], 1))
        data['ZEWK'] = data['ZEWS'] * rflz_reshaped
        
        # Find total service area in Mvkm, first by tech, then by vehicle class
        data['ZEVV'] = data['ZEWK'] * data['BZTC'][:, :, c6ti['15 Average mileage (km/y)'], np.newaxis] / 10e6
        data['ZESG'] = sum_over_classes(data['ZEVV'])
        
        # Calculate demand in million ton vehicle-km OR million passenger vehicle km, per vehicle class
        data['ZEST'] = data['ZEVV'] * data['BZTC'][:, :, c6ti['10 Loads (t or passengers/veh)'], np.newaxis]
        data['RVKZ'] = sum_over_classes(data['ZEST'])
        
        # Emissions 
        data['ZEWE'] = (data['ZEVV']
                        * data['BZTC'][:, :, c6ti['12 CO2 emissions (gCO2/km)'], np.newaxis]
                        * (1 - data['ZBFM']) / (1e6) )
        
        for r in range(len(titles['RTI'])):
        
            for veh in range(len(titles['FTTI'])):
                for fuel in range(len(titles['JTI'])):
                    if titles['JTI'][fuel] == '11 Biofuels' and data['ZJET'][0, veh, fuel] == 1:
                        # No biofuel blending mandate in the historical period
                        zjet[veh, fuel] = 0
                        
            # Find fuel use
            data['ZJNJ'][r, :, 0] = (np.matmul(np.transpose(zjet), data['ZEVV'][r, :, 0] * \
                                    data['BZTC'][r, :, c6ti['9 Energy use (MJ/vkm)']])) / 41.868

        if year == histend["RFLZ"]:
            # Calculate levelised cost
            data = get_lcof(data, titles)


    "Model Dynamics"

    # Endogenous calculation starts here
    if year > histend['RFLZ']:

        data_dt = {}
        data_dt['ZWIY'] = np.zeros([len(titles['RTI']), len(titles['FTTI']), 1])

        
        for var in time_lag.keys():
            if var.startswith(("R", "Z", "B")):
                data_dt[var] = np.copy(time_lag[var])
                

        # Find if there is a regulation and if it is exceeded
        division = divide((time_lag['ZEWK'][:, :, 0] - data['ZREG'][:, :, 0]),
                           data['ZREG'][:, :, 0]) # 0 when dividing by 0
        isReg = 0.5 + 0.5 * np.tanh(1.5 + 10 * division)
        isReg[data['ZREG'][:, :, 0] == 0.0] = 1.0
        isReg[data['ZREG'][:, :, 0] == -1.0] = 0.0


        
        
        for t in range(1, no_it + 1):
        # Interpolations to avoid staircase profile

            D = time_lag['RVKZ'] + (data['RVKZ'] - time_lag['RVKZ']) * t * dt
            Utot = time_lag['RFLZ'] + (data['RFLZ'] - time_lag['RFLZ']) * t * dt
            Utot = np.tile(Utot, (1, data['ZEWS'].shape[1] // Utot.shape[1], 1))[:, :, 0] # Reshape to 71 x #tech (duplicate info)
           
            endo_shares, endo_capacity = shares(
                dt, t, no_it, data_dt['ZEWS'], data_dt['ZEGC'], data_dt['ZTTD'], data['ZEWA'],
                data['BZTC'][:, :, c6ti['14 Turnover rate (1/y)']], isReg,
                D, Utot, titles)
            
            zews = implement_shares_policies(
                endo_capacity, endo_shares, 
                titles, data['ZWSA'], data['ZREG'], isReg,
                sum_over_classes, n_veh_classes, Utot, no_it)
            
            data['ZEWS'] = zews
            
                    
            # Copy over costs that don't change
            data['BZTC'][:, :, 1:20] = data_dt['BZTC'][:, :, 1:20]

            # This is number of trucks by technology
            data['ZEWK'] = data['ZEWS'] * Utot[:, :, None]
            
            # Find total service area and demand, first by tech, then by vehicle class     
            data['ZEVV'] = data['ZEWK'] * data['BZTC'][:, :, c6ti['15 Average mileage (km/y)'], np.newaxis] / 10e6
            data['ZEST'] = data['ZEVV'] * data['BZTC'][:, :, c6ti['10 Loads (t or passengers/veh)'], np.newaxis]
            data['ZESG'] = sum_over_classes(data['ZEVV'])
            data['RVKZ'] = sum_over_classes(data['ZEST'])
                                    
            # Emissions
            data['ZEWE'] = ( data['ZEVV']
                            * data['BZTC'][:, :, c6ti['12 CO2 emissions (gCO2/km)'], None]
                            * (1 - data['ZBFM']) / 1e6 )
            
            # Reopen country loop
            for r in range(len(titles['RTI'])):

                if np.sum(D[r]) == 0.0:
                    continue
                
                                        
                zjet = np.copy(data['ZJET'][0, :, :])
                for veh in range(len(titles['FTTI'])):
                    for fuel in range(len(titles['JTI'])):
                        #  Middle distillates
                        if titles['JTI'][fuel] == '5 Middle distillates' and data['ZJET'][0, veh, fuel]  == 1:  

                            #  Mix with biofuels if there's a biofuel mandate
                            zjet[veh, fuel] = zjet[veh, fuel] * (1.0 - data['ZBFM'][r, 0, 0])

                            # Emission correction factor
                            emis_corr[r, veh] = 1.0 - data['ZBFM'][r, 0, 0]

                        elif titles['JTI'][fuel] == '11 Biofuels' and data['ZJET'][0, veh, fuel] == 1:

                            zjet[veh, fuel] = data['ZJET'][0, veh, fuel] * data['ZBFM'][r, 0, 0]

                # Fuel use by fuel type - Convert TJ (BZTC * ZEVV) to ktoe, so divide by 41.868
                data['ZJNJ'][r, :, 0] = (np.matmul(np.transpose(zjet), data['ZEVV'][r, :, 0] * \
                                    data['BZTC'][r, :, c6ti['9 Energy use (MJ/vkm)']])) / 41.868
            

            # Investment (sales) = new capacity created
            # zewi_t is new additions at current timestep/iteration
            data, zewi_t = get_sales(data, data_dt, time_lag, titles, dt, c6ti, t)
            
            # Cumulative investment, not in region loop as it is global
            bi = np.matmul(zewi_t[:, :, 0], data['ZEWB'][0, :, :])
            dw = np.sum(bi, axis=0)
            
            data['ZEWW'][0, :, 0] = data_dt['ZEWW'][0, :, 0] + dw
            
            
            # Learning-by-doing effects on investment
            for tech in range(len(titles['FTTI'])):

                if data['ZEWW'][0, tech, 0] > 0.1:

                    data['BZTC'][:, tech, c6ti['1 Purchase cost (USD/veh)']] =  \
                            data_dt['BZTC'][:, tech, c6ti['1 Purchase cost (USD/veh)']] \
                            * (1.0 + data["BZTC"][:, tech, c6ti['13 Learning exponent']]
                            * dw[tech]/data['ZEWW'][0, tech, 0])


            # Calculate total investment by technology in terms of truck purchases
            data['ZWIY'] = data['ZEWI'] * data["BZTC"][r, :, c6ti['1 Purchase cost (USD/veh)'], None]

            # Calculate levelised cost again
            data = get_lcof(data, titles)


            for var in time_lag.keys():
                if var.startswith(("R", "Z", "B")):
                    data_dt[var] = np.copy(data[var])


    return data
