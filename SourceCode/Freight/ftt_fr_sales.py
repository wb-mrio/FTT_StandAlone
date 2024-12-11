# -*- coding: utf-8 -*-
"""
Created on Wed Apr 03 15:45:37 2024

@author: CL
"""

import numpy as np

# %% new sales
# -----------------------------------------------------------------------------
# -----------------------Calculation of new sales (ZEWI)-----------------------
# -----------------------------------------------------------------------------
def get_sales(data, data_dt, time_lag, titles, dt, c6ti, t):
    """
    Calculate new sales/additions in FTT-Freight.

    This function calculates the amount of new vehicle sales required (ZEWI).
    ZEWI is calculated in number of vehicles. This is based on:

    1. If capacity has grown, the difference between the new capacity and the
       old.
    2. The amount of existing capacity that is depreciated (retired) as it
       reaches its end of life.
    
    Capacity depreciation is currently based on the vehicle lifetime in the
    cost matrix. This means 1/vehicle lifetime of capacity is retired every
    year.

    Parameters
    -----------
    data: dictionary
        Data is a container that holds all cross-sectional (of time) for all
        variables. Variable names are keys and the values are 3D NumPy arrays.
    data_dt: dictionary
        Data_dt is a container that holds all cross-sectional (of time) data
        for all variables of the previous iteration.
    time_lag: dictionary
        Time_lag is a container that holds all cross-sectional (of time) data
        for all variables of the previous year.
    titles: dictionary
        Titles is a container of all permissible dimension titles of the model.
    dt: integer
        Dt is an integer - 1 / number of iterations.

    Returns
    ----------
    data: dictionary
        Data is a container that holds all cross-sectional (of time) data for
        all variables.
        Variable names are keys and the values are 3D NumPy arrays.
        The values inside the container are updated and returned to the main
        routine.
    zewi_t: 
    
    """
    # Find the difference in capacity between this iteration and last
    cap_diff = data['ZEWK'][:, :, 0] - data_dt['ZEWK'][:, :, 0]
    # Initialise variable for amount of capacity depreciated
    cap_drpctn = np.zeros([len(titles['RTI']), len(titles['FTTI']), 1])
    # If capacity has grown, additions equal the difference +
    # depreciation from the previous year.
    # Otherwise, additions just equal depreciations.
    # Where capacity has decreased, we only add new capacity
    # if the depreciation > capacity loss
    for r in range(len(titles['RTI'])):
        for veh in range(len(titles['FTTI'])):
            cap_drpctn[r, veh, 0] = np.where(cap_diff[r, veh] > 0.0,
                                data_dt["ZEWK"][r, veh, 0] * dt / data['BZTC'][r, veh, c6ti['8 Lifetime (y)']],
                                np.where((-data_dt["ZEWS"][r, veh, 0] * dt / data['BZTC'][r, veh, c6ti['8 Lifetime (y)']] 
                                          < data["ZEWS"][r, veh, 0] - data_dt["ZEWS"][r, veh, 0] < 0),
                                            (data["ZEWS"][r, veh, 0] - data_dt["ZEWS"][r, veh, 0] 
                                             + data_dt["ZEWS"][r,veh,0] * dt / data['BZTC'][r, veh, c6ti['8 Lifetime (y)']])
                                             * time_lag["ZEWK"][r, veh, 0], 0))
            # Catch any negative values
            if cap_drpctn[r, veh, 0] < 0:
                cap_drpctn[r, veh, 0] = 0

    # Find total additions at time t
    zewi_t = np.zeros([len(titles['RTI']), len(titles['FTTI']), 1],)
    zewi_t[:, :, 0] = np.where(cap_diff[:, :] > 0.0,
                                cap_diff[:, :] + cap_drpctn[:, :, 0],
                                cap_drpctn[:, :, 0])
        
    # Reset new additions if first FTT iteration
    if (t == 1):
        data["ZEWI"][: ,: ,0] = 0
    # Add additions at iteration t to total annual additions
    data["ZEWI"][:, :, 0] = data["ZEWI"][:,:,0] + zewi_t[:,:,0]

    return data, zewi_t