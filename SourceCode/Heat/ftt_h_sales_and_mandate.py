import numpy as np


green_indices = [9, 10, 11]  # Indices for heat pumps
MANDATE_START_YEAR = 2025
N_YEARS = 11  
MANDATE_END_YEAR = MANDATE_START_YEAR + N_YEARS

from SourceCode.ftt_core.ftt_mandate import get_new_sales_under_mandate, get_mandate_share



def get_enhanced_sales(cap, cap_dt, cap_lag, shares, shares_dt, sales_or_investment_in,
                       HETR, dt, hp_mandate, year):
    # Step 1: Calculate basic components
    cap_growth = cap[:, :, 0] - cap_lag[:, :, 0]
    share_growth_dt = shares[:, :, 0] - shares_dt[:, :, 0]
    cap_growth_dt = cap[:, :, 0] - cap_dt[:, :, 0]
    base_eol = cap_dt[:, :, 0] * dt * HETR
    share_depreciation = shares_dt[:, :, 0] * dt * HETR


    # Step 2: Initialize sales array
    sales_dt = np.zeros(sales_or_investment_in.shape)


    # Step 3: Compute initial sales
    for r in range(cap.shape[0]):
        for tech in range(cap.shape[1]):
            if cap_growth_dt[r, tech] > 0:
                sales_dt[r, tech, 0] = cap_growth_dt[r, tech] + base_eol[r, tech]
            elif -share_depreciation[r, tech] < share_growth_dt[r, tech] < 0:
                replacement_sales = (share_growth_dt[r, tech] + share_depreciation[r, tech]) * cap_lag[r, tech, 0]
                sales_dt[r, tech, 0] = max(0, replacement_sales) 
            else:
                sales_dt[r, tech, 0] = base_eol[r, tech]

    # Step 4: Apply mandate adjustments with global shares and strict enforcement
    if hp_mandate[0,0,0] == 1 :
        mandate_share = get_mandate_share(year, MANDATE_START_YEAR, MANDATE_END_YEAR)
        sales_after_mandate = get_new_sales_under_mandate(sales_dt, mandate_share, green_indices)
        
        sales_difference = sales_after_mandate - sales_dt
        cap = cap + sales_difference
        cap = np.maximum(cap, 0)
        
        sales_dt = np.copy(sales_after_mandate)

   

    # Step 6: Update cumulative sales
    sales_or_investment = np.copy(sales_or_investment_in)
    sales_or_investment[:, :, 0] += sales_dt[:, :, 0]


    return sales_or_investment, sales_dt, cap


