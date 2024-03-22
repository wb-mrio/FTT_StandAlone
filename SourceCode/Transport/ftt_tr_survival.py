# -*- coding: utf-8 -*-
"""
Created on Fri Jan  5 14:38:50 2024
TODO: use pre-simulation TEWK values to improve the age distribution before simulation starts
"""

import numpy as np
import copy


def get_survival_ratio(survival_function):
    """Transform survival function
    into a year-on-year ratio of survival.
    
    The survival ratio is reshapen to work with RLTA"""
    
    survival_ratio = survival_function[:, :-1, :] / survival_function[:, 1:, :] 
    survival_ratio = survival_ratio.reshape(71, 1, 22)
    return survival_ratio

def add_new_cars_age_matrix(age_matrix, capacity, lagged_capacity, scrappage):
    """Add new cars to the age matrix.
    Add the growth in capacity (pos or neg) to the scrappage    
    
    New car additions are set to zero if calculation is negative (f.i. with regulation)
    
    """
    capacity_growth = capacity - lagged_capacity
    new_cars = capacity_growth[:, :, 0] + scrappage[:, :, 0]
    # Set new cars to zero
    new_cars = np.where(new_cars < 0, 0, new_cars)
    
    age_matrix[:, :, 22] = new_cars
    
    # Normalise age_matrix, so that in each country + car, it sums to overall capacity TEWK. 
    age_matrix = age_matrix * capacity / np.sum(age_matrix, axis=2, keepdims=True)
    
    return age_matrix

def initialise_age_matrix(data, time_lag, titles, survival_ratio):
    """At the start of the simulation, set up an age matrix, assuming
    an equilibrium has been reached"""
    
    # VYTI has 23 year categories (number 0-22)
    # TODO: This needs to be replaced with actual data
    fraction_per_age = np.linspace(1/(3*len(titles['VYTI'])), 3/len(titles['VYTI']), len(titles['VYTI'])) * 0.6
    
    # Split the capacity TEWK into different age brackets via broadcasting
    data["RLTA"] = fraction_per_age[None, None, :] * data["TEWK"][:, :, 0][:, :, np.newaxis]

    # Sum over the age dimension
    survival = np.sum(data['RLTA'][:, :, 1:] * survival_ratio[:, :, :], axis=2)
    data['REVS'][:, :, 0] = time_lag["TEWK"][:, :, 0] - survival
    return data
    

def survival_function(data, time_lag, histend, year, titles):
    """
    Survival function for each car type
    
    We calculate the number of cars by age bracket (RLTA) and scrappage (REVS), 
    Ultimately, we want to include sales and average efficiency in this function too.
        
    Returns
    ----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution
    """
        
    survival_ratio = get_survival_ratio(data['TESF'])
    
    # We assume a linearly decreasing distribution of ages at initialisation
    if np.sum(time_lag["RLTA"])==0:
         initialise_age_matrix(data, time_lag, titles, survival_ratio)   

    else:
        # After the first year of historical data, we can start calculating 
        # the age matrix endogenously. This allows us to calculate scrappage,
        # sales, average age, and average efficiency.
        
        # Move all vehicles one year up
        data['RLTA'][..., :-1] = np.copy(time_lag['RLTA'][..., 1:])
        
        # Apply the survival ratio
        data['RLTA'][..., :-1] *= survival_ratio
        
        # Set the newest car category to zero
        data['RLTA'][..., -1] = 0
        
        # Calculate survival and handle EoL vehicle scrappage
        survival = np.sum(data['RLTA'], axis=-1)
        survival_diff = time_lag['TEWK'][..., 0] - survival
        
        # Vectorized condition for scrappage
        data['REVS'][..., 0] = np.where(survival_diff > 0, survival_diff, 0)
        
        # Warning if more cars survive than existed previous timestep:
        for r in range(data['RLTA'].shape[0]):
            for veh in range(data['RLTA'].shape[1]):
                if time_lag['TEWK'][r, veh, 0] < np.sum(data['RLTA'][r, veh, :]):
                    msg = (f"Error! \n"
                           f"Check year {year}, region - {titles['RTI'][r]}, vehicle - {titles['VTTI'][veh]}\n"
                           "More cars survived than what was in the fleet before:\n"
                           f"{time_lag['TEWK'][r, veh, 0]:.4f} versus {np.sum(data['RLTA'][r, veh, :]):.4f}")
                    print(msg)

    return data