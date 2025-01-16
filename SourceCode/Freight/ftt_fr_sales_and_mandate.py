# -*- coding: utf-8 -*-


import numpy as np

from SourceCode.ftt_core.ftt_mandate import get_new_sales_under_mandate, get_mandate_share


green_indices = range(30, 35)  # Indices for green technologies
MANDATE_START_YEAR = 2025
N_YEARS = 16


def implement_mandate(cap, EV_truck_mandate, cum_sales_in, sales_in, n_veh_classes, year):    
    
    cum_sales_after_mandate = np.copy(cum_sales_in)
    sales_after_mandate = np.copy(sales_in)
    mandate_end_year = MANDATE_START_YEAR + N_YEARS

    
    if EV_truck_mandate[0, 0, 0] in range(2010, 2040) and year > EV_truck_mandate[0, 0, 0]:
        # For the sequencing, I'm changing the end year
        mandate_end_year = EV_truck_mandate[0, 0, 0]
        
        
    # Step 4: Apply mandate adjustments with global shares and strict enforcement
    mandate_share = get_mandate_share(year, MANDATE_START_YEAR, mandate_end_year)
        

    if EV_truck_mandate[0, 0, 0] not in [-1, 0] and np.sum(mandate_share) > 0:
        
        for veh_class in range(n_veh_classes):
            sales_in_class = sales_in[:, veh_class::n_veh_classes, :]
            green_indices_class = [6]
            
            # Recompute sales, after implementation of mandate
            sales_after_mandate_class = get_new_sales_under_mandate(sales_in_class, mandate_share, green_indices_class)
            sales_after_mandate[:, veh_class::n_veh_classes] = sales_after_mandate_class
    
            # Step 5: Update capacity
            sales_difference = sales_after_mandate_class - sales_in_class
            cap[:, veh_class::n_veh_classes, :] = cap[:, veh_class::n_veh_classes, :] + sales_difference
            cap[:, veh_class::n_veh_classes, 0] = np.maximum(cap[:, veh_class::n_veh_classes, 0], 0)
            
            # Step 6: Update cumulative sales
            cum_sales_after_mandate[:, veh_class::n_veh_classes, 0] += sales_difference[:, :, 0]
        
        return cum_sales_after_mandate, sales_after_mandate, cap
    
    # If there is no mandate
    else:
        return cum_sales_in, sales_in, cap


