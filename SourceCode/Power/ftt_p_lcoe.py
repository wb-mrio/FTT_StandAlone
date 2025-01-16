# -*- coding: utf-8 -*-
"""
=========================================
ftt_p_lcoe.py
=========================================
Power LCOE FTT module.


Functions included:
    - get_lcoe
        Calculate levelized costs

"""

# Third party imports
import numpy as np



# %% lcoe
# -----------------------------------------------------------------------------
# --------------------------- LCOE function -----------------------------------
# -----------------------------------------------------------------------------
def set_carbon_tax(data, c2ti, year):
    '''
    Convert the carbon price in REPP from euro / tC to $2013 dollars. 
    Apply the carbon price to power sector technologies based on their efficiencies

    The function changes data.
    
    REX --> EU local currency per euros rate (33 is US$)
    PRSC --> price index (local currency) consumer expenditure
    EX --> EU local currency per euro, 2005 == 1
    The 13 part of the variable mean denotes 2013. 
    '''
    
    carbon_costs = (
                    data['BCET'][:, :, c2ti['15 Emissions (tCO2/GWh)']]   # Emission per GWh
                    * data["REPPX"][:, :, 0]                              # Carbon price in euro / tC
                    * data["REX13"][33, 0, 0] / ( data["PRSCX"][:, :, 0] * data["EX13"][:, :, 0] / (data["PRSC13"][:, :, 0]  * data["EXX"][:, :, 0]) )
                    / 1000 / 3.666                                        # Conversion from GWh to MWh and from C to CO2. 
                    )
    
    
    if np.isnan(carbon_costs).any():
        print(f"Carbon price is nan in year {year}")
        print(f"The arguments of the nans are {np.argwhere(np.isnan(carbon_costs))}")
        print( ('Conversion factor:'
              f'{data["REX13"][33, 0, 0] / ( data["PRSCX"][:, :, 0] * data["EX13"][:, :, 0] / (data["PRSC13"][:, :, 0]  * data["EXX"][:, :, 0]) )}') )
        print(f"Emissions intensity {data['BCET'][:, :, c2ti['15 Emissions (tCO2/GWh)']]}")
        
        raise ValueError
                       
    return carbon_costs
    

def get_lcoe(data, titles):
    """
    Calculate levelized costs.

    The function calculates the levelised cost of electricity in $2013/MWh. It includes
    intangible costs (gamma values) and determines the investor preferences.

    Parameters
    -----------
    data: dictionary of NumPy arrays
        Model variables for the current year.
        Variable names are keys and the values are 3D NumPy arrays.
    titles: dictionary
        Titles is a container of all permissible dimension titles of the model.

    Returns
    ----------
    data: dictionary
        Updated values:
            The different LCOE variants (METC, MECW ..)
            The standard deviation of LCOE (MTCD)
            The components of LCOE (MCFC, MWIC)

    Notes
    ---------
    BCET = cost matrix 
    MEWL = Average capacity factor
    MEWT = Subsidies
    MTFT = Fuel tax
    
    """

    # Categories for the cost matrix (BCET)
    c2ti = {category: index for index, category in enumerate(titles['C2TI'])}

    for r in range(len(titles['RTI'])):

        # Cost matrix
        bcet = data['BCET'][r, :, :]

        # Plant lifetime
        lt = bcet[:, c2ti['9 Lifetime (years)']]
        bt = bcet[:, c2ti['10 Lead Time (years)']]
        max_lt = int(np.max(bt+lt))
        
        # Define (matrix) masks to turn off cost components before or after contruction 
        full_lt_mat = np.linspace(np.zeros(len(titles['T2TI'])), max_lt - 1, num=max_lt, axis=1, endpoint=True)
        lt_max_mat = np.concatenate([(lt + bt - 1)[:, np.newaxis]] * max_lt, axis=1)
        bt_max_mat = np.concatenate([(bt - 1)[:, np.newaxis]] * max_lt, axis=1)

        bt_mask = full_lt_mat <= bt_max_mat
        lt_mask = full_lt_mat <= lt_max_mat
        
        # Capacity factor of marginal unit (for decision-making) # Trap for very low CF
        cf_mu = np.maximum(bcet[:, c2ti['11 Decision Load Factor']], 0.000001)
        
        # Factor to transfer cost components in terms of capacity to generation
        conv_mu = 1 / bt / cf_mu / 8766 * 1000
        
        # Average capacity factor (for electricity price) # Trap for very low CF
        cf_av = np.maximum(data['MEWL'][r, :, 0], 0.000001)
        
        # Factor to transfer cost components in terms of capacity to generation
        conv_av = 1 / bt / cf_av / 8766 * 1000
        
        # Discount rate
        dr = bcet[:, c2ti['17 Discount Rate (%)'], np.newaxis]
        
        # Helper function to extract cost
        def extract_costs(column, mask, conv_factor=None):
            '''
            This helper function extracts costs from the 'bcet' data, applies masking to zero out
            specific elements, and optionally scales the values based on a conversion factor.
            
            Scaling adjusts the extracted data values using a conversion factor to account for 
            unit conversion, normalization, or context-specific adjustments.
            '''
            
            # Extract the matrix with data from the specified column
            matrix = np.ones([len(titles['T2TI']), max_lt]) * bcet[:, c2ti[column], np.newaxis]
            
            if conv_factor is not None:
                matrix *= conv_factor[:, np.newaxis]
                
            # Apply the mask to zero out specific elements if a mask is provided; otherwise, return the unmasked matrix
            return np.where(mask, matrix, 0)

        # Initialse the levelised cost components
        # Average investment cost of marginal unit (new investments)
        it_mu = extract_costs('3 Investment ($/kW)', bt_mask, conv_mu)
        
        # Average investment costs of across all units (electricity price)
        it_av = extract_costs('3 Investment ($/kW)', bt_mask, conv_av)

        # Standard deviation of investment cost - marginal unit
        dit_mu = extract_costs('4 std ($/MWh)', bt_mask, conv_mu)

        # Standard deviation of investment cost - average of all units
        dit_av = extract_costs('4 std ($/MWh)', bt_mask, conv_av)

        # Subsidies - only valid for marginal unit
        st = extract_costs('3 Investment ($/kW)', bt_mask, conv_mu)
        st *= data['MEWT'][r, :, :]

        # Average fuel costs
        ft = extract_costs('5 Fuel ($/MWh)', mask=lt_mask)

        # Standard deviation of fuel costs
        dft = extract_costs('6 std ($/MWh)', mask=lt_mask)

        # fuel tax/subsidies
        fft = np.ones([len(titles['T2TI']), max_lt]) * data['MTFT'][r, :, 0, np.newaxis]
        fft = np.where(lt_mask, fft, 0)

        # Average operation & maintenance cost
        omt = extract_costs('7 O&M ($/MWh)', mask=lt_mask)

        # Standard deviation of operation & maintenance cost
        domt = extract_costs('8 std ($/MWh)', mask=lt_mask)

        # Carbon costs
        ct = extract_costs('1 Carbon Costs ($/MWh)', mask=lt_mask)
        
        # Standard deviation carbon costs (set to zero for now)
        dct = extract_costs('2 std ($/MWh)', mask=lt_mask)

        # Energy production over the lifetime (incl. buildtime)
        # No generation during the buildtime, so no benefits
        energy_prod = np.ones([len(titles['T2TI']), int(max_lt)])
        energy_prod = np.where(lt_mask, energy_prod, 0)

        # Storage costs and marginal costs (lifetime only)
        stor_cost, marg_stor_cost = np.zeros_like(ft), np.zeros_like(ft)
        
        if np.rint(data['MSAL'][r, 0, 0]) in [2]:
            stor_cost = (data['MSSP'][r, :, 0, np.newaxis] + data['MLSP'][r, :, 0, np.newaxis]) / 1000
        elif np.rint(data['MSAL'][r, 0, 0]) in [3, 4, 5]:
            stor_cost = (data['MSSP'][r, :, 0, np.newaxis] + data['MLSP'][r, :, 0, np.newaxis]) / 1000
            marg_stor_cost = (data['MSSM'][r, :, 0, np.newaxis] + data['MLSM'][r, :, 0, np.newaxis]) / 1000

        stor_cost = np.where(lt_mask, stor_cost, 0)
        
        marg_stor_cost = np.where(lt_mask, marg_stor_cost, 0)

        dstor_cost = 0.2 * stor_cost  # Assume standard deviation of 20%

        # Net present value calculations
        
        # Discount rate
        denominator = (1+dr)**full_lt_mat
        
        # 1a – Expenses – marginal units
        npv_expenses_mu_no_policy      = (it_mu + ft + omt + stor_cost) / denominator 
        npv_expenses_mu_only_co2       = npv_expenses_mu_no_policy + ct / denominator
        npv_expenses_mu_all_policies   = npv_expenses_mu_no_policy + (ct + fft + st + marg_stor_cost) / denominator 
        
        # 1b – Expenses – average LCOEs
        npv_expenses_no_policy        = (it_av + ft + omt + stor_cost) / denominator  
        npv_expenses_all_but_co2      = npv_expenses_no_policy + (fft + st) / denominator
        
        # 2 – Utility
        npv_utility = energy_prod / denominator
        utility_tot = np.sum(npv_utility, axis=1) 
        
        # 3 – Standard deviation (propagation of error)
        npv_std = np.sqrt(dit_mu**2 + dft**2 + domt**2 + dct**2 + dstor_cost**2) / denominator  
        
        # 4a – levelised cost – marginal units 
        lcoe_mu_no_policy       = np.sum(npv_expenses_mu_no_policy, axis=1) / utility_tot        
        lcoe_mu_only_co2        = np.sum(npv_expenses_mu_only_co2, axis=1) / utility_tot 
        lcoe_mu_all_policies    = np.sum(npv_expenses_mu_all_policies, axis=1) / utility_tot - data['MEFI'][r, :, 0]
        lcoe_mu_gamma           = lcoe_mu_all_policies + data['MGAM'][r, :, 0]

        # 4b levelised cost – average units 
        lcoe_all_but_co2        = np.sum(npv_expenses_all_but_co2, axis=1) / utility_tot - data['MEFI'][r, :, 0]    
        
        # Standard deviation of LCOE
        dlcoe                   = np.sum(npv_std, axis=1) / utility_tot


        # Pass to variables that are stored outside.
        data['MEWC'][r, :, 0] = lcoe_mu_no_policy       # The real bare LCOE without taxes
        data['MECW'][r, :, 0] = lcoe_mu_only_co2        # Bare LCOE with CO2 costs
        data["MECC"][r, :, 0] = lcoe_all_but_co2        # LCOE with policy, without CO2 costs
        data['METC'][r, :, 0] = lcoe_mu_gamma           # As seen by consumer (generalised cost)
        data['MTCD'][r, :, 0] = dlcoe                   # Standard deviation LCOE 


        # Output variables
        data['MWIC'][r, :, 0] = bcet[:, c2ti['3 Investment ($/kW)']]    # Investment cost component LCOE ($/kW)
        data['MWFC'][r, :, 0] = bcet[:, c2ti['5 Fuel ($/MWh)']]    # Fuel cost component of the LCOE ($/MWh)
        data['MCOC'][r, :, 0] = bcet[:, c2ti['1 Carbon Costs ($/MWh)']]    # Carbon cost component of the LCOE ($/MWh)
        data['MCFC'][r, :, 0] = bcet[:, c2ti['11 Decision Load Factor']].copy() # The (marginal) capacity factor 

        # MWMC: FTT Marginal costs power generation ($/MWh)
        if np.rint(data['MSAL'][r, 0, 0]) > 1: # rint rounds to nearest int
            data['MWMC'][r, :, 0] = bcet[:, 0] + bcet[:, 4] + bcet[:, 6] + (data['MSSP'][r, :, 0] + data['MLSP'][r, :, 0])/1000
        else:
            data['MWMC'][r, :, 0] = bcet[:, 0] + bcet[:, 4] + bcet[:, 6]


        # Marginal cost standard deviation (MMCD)
        data['MMCD'][r, :, 0] = np.sqrt(
            bcet[:, 1] ** 2 + bcet[:, 5] ** 2 + bcet[:, 7] ** 2
        )
        
        # Check if METC is nan
        if np.isnan(data['METC']).any():
            nan_indices_metc = np.where(np.isnan(data['METC']))
            raise ValueError(f"NaN values detected in lcoe ('metc') at indices: {nan_indices_metc}")

    return data
