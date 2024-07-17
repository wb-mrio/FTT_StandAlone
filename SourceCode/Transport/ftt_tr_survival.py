# -*- coding: utf-8 -*-
"""
Created on Fri Jan  5 14:38:50 2024

These function construct a age bracket matrix from historical and simulated
car numbers per country. 

The logic is that a fixed percentage of cars per age bracket are scrapped. 
New cars are the sum of growth in car numbers and scappage. 

This means the new car numbers can be quite volatile, especially historically

"""

import numpy as np


def get_survival_ratio(survival_function_array):
    """Transform survival function into a year-on-year ratio of survival.
    
    The survival ratio is reshapen to work with RLTA
    
    Returns:
        survival ratio with shape (country, None, age brackets)
    """
    survival_ratio = survival_function_array[:, :-1, :] / survival_function_array[:, 1:, :]
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
    
    # Sum over each age bracket. This should be equal to TEWK.
    sum_age_matrix = np.sum(age_matrix, axis=2, keepdims=True)
    
        # Check for NaNs
    if np.any(np.isnan(sum_age_matrix)):
        print("NaN values found in sum_age_matrix.")
    
    if np.any(np.isnan(age_matrix)):
        print("NaN values found in age_matrix.")
    
    # Normalise age_matrix, so that in each country + car, it sums to overall capacity TEWK.
    age_matrix = np.divide(age_matrix * capacity, sum_age_matrix, \
                           where=sum_age_matrix!=0, out=np.zeros_like(age_matrix))

    return age_matrix

def initialise_age_matrix(data, titles):
    """At the start of the simulation, set up an age matrix, assuming
    an equilibrium has been reached
    
    # TODO: This needs to be replaced with actual data?
    """
    
    # VYTI has 23 year categories (number 0-22)
    n_age_brackets = len(titles['VYTI'])
    fraction_per_age = np.linspace(1/(3*n_age_brackets), 3/n_age_brackets, n_age_brackets)
    fraction_per_age = fraction_per_age / np.sum(fraction_per_age)
    
    # Split the capacity TEWK into different age brackets via broadcasting
    data["RLTA"] = fraction_per_age[None, None, :] * data["TEWK"][:, :, 0][:, :, np.newaxis]

    return data
    

def survival_function(data, time_lag, histend, year, titles):
    """
    Survival function for each car type
    
    We calculate the number of cars by age bracket (RLTA) and scrappage (REVS), 
    Ultimately, we want to include sales and average efficiency in this function too.
        
    Returns
    ----------
    data: dictionary of NumPy arrays
        Model variables for the current year
    """
        
    survival_ratio = get_survival_ratio(data['TESF'])
    
    # We assume a linearly decreasing distribution of ages at initialisation
    if np.sum(time_lag["RLTA"]) == 0:
        initialise_age_matrix(data, titles)   
    
    # After the first year of historical data, we start calculating the age
    # matrix endogenously.
    else:
        
        # Move all vehicles one year up
        data['RLTA'][..., :-1] = np.copy(time_lag['RLTA'][..., 1:])
        
        # Apply the survival ratio
        data['RLTA'][..., :-1] *= survival_ratio
        
        # Calculate survival and handle EoL vehicle scrappage
        survival = np.sum(data['RLTA'], axis=-1)
        scrappage = time_lag['TEWK'][..., 0] - survival
        
        # Vectorized condition for scrappage
        data['REVS'][..., 0] = np.where(scrappage > 0, scrappage, 0)
        
        
        # Warning if more cars survive than existed previous timestep:
        for r in range(data['RLTA'].shape[0]):
            for veh in range(data['RLTA'].shape[1]):
                if not np.isclose(time_lag['TEWK'][r, veh, 0], survival[r, veh], atol=1e-6) and time_lag['TEWK'][r, veh, 0] < survival[r, veh]:
                    msg = (f"Error! \n"
                           f"Check year {year}, region - {titles['RTI'][r]}, vehicle - {titles['VTTI'][veh]}\n"
                           "More cars survived than what was in the fleet before:\n"
                           f"{time_lag['TEWK'][r, veh, 0]:.8f} versus {np.sum(data['RLTA'][r, veh, :]):.8f}")
                    print(msg)
    
    data["RLTA"] = add_new_cars_age_matrix(
                data["RLTA"], data["TEWK"], time_lag["TEWK"], data["REVS"]
                )

    return data
