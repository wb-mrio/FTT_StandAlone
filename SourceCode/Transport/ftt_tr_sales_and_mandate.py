import numpy as np
import copy

green_indices = [18, 19, 20]  # Indices for green technologies
MANDATE_START_YEAR = 2025
N_YEARS = 11
MANDATE_END_YEAR = MANDATE_START_YEAR + N_YEARS

def calculate_mandate_share(year):
    """Calculate the mandate share based on the year."""
    if year < MANDATE_START_YEAR:
        return 0.0
    elif year >= MANDATE_END_YEAR:
        return 0.0
    else:
        # Linear increase from 0 to 1 between start and end years
        return (year - MANDATE_START_YEAR) / (MANDATE_END_YEAR - MANDATE_START_YEAR)

def get_enhanced_sales(cap, cap_dt, cap_lag, shares, shares_dt, sales_or_investment_in, 
                      timescales, dt, EV_mandate, year):
    # Common calculations for both cases
    cap_growth = cap[:, :, 0] - cap_lag[:, :, 0]
    share_growth_dt = shares[:, :, 0] - shares_dt[:, :, 0]
    cap_growth_dt = cap[:, :, 0] - cap_dt[:, :, 0]
    share_depreciation = shares_dt[:, :, 0] * dt / timescales

    # Base EOL calculation for both cases
    conditions = [
        (cap_growth >= 0.0),
        (-share_depreciation < share_growth_dt) & (share_growth_dt < 0)
    ]
    outputs_eol = [
        cap_dt[:, :, 0] * dt / timescales,
        (share_growth_dt + share_depreciation) * cap_lag[:, :, 0]
    ]
    eol_replacements = np.select(conditions, outputs_eol, default=0)
    eol_replacements = np.maximum(eol_replacements, 0)

    # Calculate base sales for both cases
    sales_dt = np.zeros(sales_or_investment_in.shape)
    sales_dt[:, :, 0] = np.where(cap_growth_dt[:, :] > 0.0,
                                cap_growth_dt[:, :] + eol_replacements,
                                eol_replacements)

    # Apply mandate adjustments if needed
    if EV_mandate[0,0,0] != 0:
        mandate_share = calculate_mandate_share(year)
        for r in range(cap.shape[0]):
            total_sales = np.sum(sales_dt[r, :, 0])
            if total_sales > 0:
                current_green = np.sum(sales_dt[r, green_indices, 0])
                current_share = current_green / total_sales

                if current_share < mandate_share:
                    target_green = total_sales * mandate_share
                    if current_green > 0:
                        scale_factor = target_green / current_green
                        sales_dt[r, green_indices, 0] *= scale_factor
                    else:
                        global_green_sales = np.sum(sales_dt[:, green_indices, 0], axis=0)
                        if np.sum(global_green_sales) > 0:
                            global_shares = global_green_sales / np.sum(global_green_sales)
                            sales_dt[r, green_indices, 0] = target_green * global_shares
                        else:
                            sales_dt[r, green_indices, 0] = target_green / len(green_indices)

                    actual_green = np.sum(sales_dt[r, green_indices, 0])
                    if actual_green < target_green:
                        sales_dt[r, green_indices, 0] *= target_green / actual_green

                    non_green_indices = [i for i in range(cap.shape[1]) if i not in green_indices]
                    remaining_sales = total_sales - target_green
                    current_non_green = np.sum(sales_dt[r, non_green_indices, 0])
                    if current_non_green > 0:
                        scale_factor = remaining_sales / current_non_green
                        sales_dt[r, non_green_indices, 0] *= scale_factor
                    elif len(non_green_indices) > 0:
                        sales_dt[r, non_green_indices, 0] = remaining_sales / len(non_green_indices)

    # Adjust capacity
    adjusted_cap_growth_dt = sales_dt[:, :, 0] - eol_replacements
    cap[:, :, 0] = cap_dt[:, :, 0] + adjusted_cap_growth_dt
    cap[:, :, 0] = np.maximum(cap[:, :, 0], 0)

    # Update cumulative sales
    sales_or_investment = sales_or_investment_in + sales_dt

    return sales_or_investment, sales_dt, cap

def get_sales_yearly_with_mandate(cap, cap_lag, shares, shares_lag, sales_or_investment_in,
                                  timescales, year, mandate_share=None, green_indices=None):
    cap_growth = cap[:, :, 0] - cap_lag[:, :, 0]
    share_growth = shares[:, :, 0] - shares_lag[:, :, 0]
    share_depreciation = shares_lag[:, :, 0] / timescales

    conditions = [
        (cap_growth >= 0.0),
        (-share_depreciation < share_growth) & (share_growth < 0)
    ]

    outputs = [
        cap_lag[:, :, 0] / timescales,
        (share_growth + share_depreciation) * cap_lag[:, :, 0]
    ]

    eol_replacements = np.select(conditions, outputs, default=0)
    eol_replacements = np.maximum(eol_replacements, 0)
    eol_replacements = eol_replacements[:, :, np.newaxis]

    sales_or_investment = np.zeros((sales_or_investment_in.shape))
    sales_or_investment[:, :, 0] = np.where(
        cap_growth[:, :] > 0.0,
        cap_growth[:, :] + eol_replacements[:, :, 0],
        eol_replacements[:, :, 0]
    )

    # Apply mandate adjustments with global shares and strict enforcement
    if mandate_share is not None and green_indices is not None:
        for r in range(cap.shape[0]):
            total_sales = np.sum(sales_or_investment[r, :, 0])
            if total_sales > 0:
                current_green = np.sum(sales_or_investment[r, green_indices, 0])
                current_share = current_green / total_sales
                
                if current_share < mandate_share:
                    target_green = total_sales * mandate_share
                    
                    # Keep existing global distribution logic
                    if current_green > 0:
                        scale_factor = target_green / current_green
                        sales_or_investment[r, green_indices, 0] *= scale_factor
                    else:
                        # Use global shares for distribution
                        global_green_sales = np.sum(sales_or_investment[:, green_indices, 0], axis=0)
                        if np.sum(global_green_sales) > 0:
                            global_shares = global_green_sales / np.sum(global_green_sales)
                            sales_or_investment[r, green_indices, 0] = target_green * global_shares
                        else:
                            sales_or_investment[r, green_indices, 0] = target_green / len(green_indices)

                    # Force minimum mandate after distribution
                    actual_green = np.sum(sales_or_investment[r, green_indices, 0])
                    if actual_green < target_green:
                        # Scale up green sales if still below target
                        sales_or_investment[r, green_indices, 0] *= target_green / actual_green
                        
                    # Adjust non-green sales to maintain total
                    non_green_indices = [i for i in range(cap.shape[1]) if i not in green_indices]
                    remaining_sales = total_sales - target_green
                    current_non_green = np.sum(sales_or_investment[r, non_green_indices, 0])
                    if current_non_green > 0:
                        scale_factor = remaining_sales / current_non_green
                        sales_or_investment[r, non_green_indices, 0] *= scale_factor
                    elif len(non_green_indices) > 0:
                        sales_or_investment[r, non_green_indices, 0] = remaining_sales / len(non_green_indices)

    cap[:, :, 0] = cap_lag[:, :, 0] + (sales_or_investment[:, :, 0] - eol_replacements[:, :, 0])
    cap[:, :, 0] = np.maximum(cap[:, :, 0], 0)

    return sales_or_investment, eol_replacements, cap