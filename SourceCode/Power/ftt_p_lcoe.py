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
    

def get_lcoe(data, titles, year):
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
        full_lt_mat = np.linspace(np.zeros(len(titles['T2TI'])), max_lt-1,
                                  num=max_lt, axis=1, endpoint=True)
        lt_max_mat = np.concatenate(int(max_lt) * [(lt+bt-1)[:, np.newaxis]], axis=1)
        bt_max_mat = np.concatenate(int(max_lt) * [(bt-1)[:, np.newaxis]], axis=1)
        
        bt_mask = full_lt_mat <= bt_max_mat
        bt_mask_out = full_lt_mat > bt_max_mat
        lt_mask_in = full_lt_mat <= lt_max_mat
        lt_mask = np.where(lt_mask_in == bt_mask_out, True, False)
        
        # Capacity factor of marginal unit (for decision-making)
        cf_mu = bcet[:, c2ti['11 Decision Load Factor']].copy()
        # Trap for very low CF
        cf_mu[cf_mu<0.000001] = 0.000001
        # Factor to transfer cost components in terms of capacity to generation
        conv_mu = 1/bt / cf_mu/8766*1000
        
        # Average capacity factor (for electricity price)
        cf_av = data['MEWL'][r, :, 0]
        # Trap for very low CF
        cf_av[cf_av<0.000001] = 0.000001
        # Factor to transfer cost components in terms of capacity to generation
        conv_av = 1/bt / cf_av/8766*1000        

        # Discount rate
        dr = bcet[:, c2ti['17 Discount Rate (%)'], np.newaxis]

        # Initialse the levelised cost components
        # Average investment cost of marginal unit (new investments)
        it_mu = np.ones([len(titles['T2TI']), int(max_lt)])
        it_mu = it_mu * bcet[:, c2ti['3 Investment ($/kW)'], np.newaxis] * conv_mu[:, np.newaxis]
        it_mu = np.where(bt_mask, it_mu, 0)
        
        # Average investment costs of across all units (electricity price)
        it_av = np.ones([len(titles['T2TI']), int(max_lt)])
        it_av = it_av * bcet[:, c2ti['3 Investment ($/kW)'], np.newaxis] * conv_av[:, np.newaxis]
        it_av = np.where(bt_mask, it_av, 0)       

        # Standard deviation of investment cost - marginal unit
        dit_mu = np.ones([len(titles['T2TI']), int(max_lt)])
        dit_mu = dit_mu * bcet[:, c2ti['4 std ($/MWh)'], np.newaxis] * conv_mu[:, np.newaxis]
        dit_mu = np.where(bt_mask, dit_mu, 0)

        # Standard deviation of investment cost - average of all units
        dit_av = np.ones([len(titles['T2TI']), int(max_lt)])
        dit_av = dit_av * bcet[:, c2ti['4 std ($/MWh)'], np.newaxis] * conv_av[:, np.newaxis]
        dit_av = np.where(bt_mask, dit_av, 0)

        # Subsidies - only valid for marginal unit
        st = np.ones([len(titles['T2TI']), int(max_lt)])
        st = (st * bcet[:, c2ti['3 Investment ($/kW)'], np.newaxis]
              * data['MEWT'][r, :, :] * conv_mu[:, np.newaxis])
        st = np.where(bt_mask, st, 0)

        # Average fuel costs
        ft = np.ones([len(titles['T2TI']), int(max_lt)])
        ft = ft * bcet[:, c2ti['5 Fuel ($/MWh)'], np.newaxis]
        ft = np.where(lt_mask, ft, 0)

        # Standard deviation of fuel costs
        dft = np.ones([len(titles['T2TI']), int(max_lt)])
        dft = dft * bcet[:, c2ti['6 std ($/MWh)'], np.newaxis]
        dft = np.where(lt_mask, dft, 0)

        # fuel tax/subsidies
        fft = np.ones([len(titles['T2TI']), int(max_lt)])
        fft = fft * data['MTFT'][r, :, 0, np.newaxis]
        fft = np.where(lt_mask, fft, 0)

        # Average operation & maintenance cost
        omt = np.ones([len(titles['T2TI']), int(max_lt)])
        omt = omt * bcet[:, c2ti['7 O&M ($/MWh)'], np.newaxis]
        omt = np.where(lt_mask, omt, 0)

        # Standard deviation of operation & maintenance cost
        domt = np.ones([len(titles['T2TI']), int(max_lt)])
        domt = domt * bcet[:, c2ti['8 std ($/MWh)'], np.newaxis]
        domt = np.where(lt_mask, domt, 0)

        # Carbon costs
        ct = np.ones([len(titles['T2TI']), int(max_lt)])
        ct = ct * bcet[:, c2ti['1 Carbon Costs ($/MWh)'], np.newaxis]
        ct = np.where(lt_mask, ct, 0)
        
        # Standard deviation carbon costs (set to zero for now)
        dct = np.ones([len(titles['T2TI']), int(max_lt)])
        dct = dct * bcet[:, c2ti['2 std ($/MWh)'], np.newaxis]
        dct = np.where(lt_mask, dct, 0)
        

        # Energy production over the lifetime (incl. buildtime)
        # No generation during the buildtime, so no benefits
        energy_prod = np.ones([len(titles['T2TI']), int(max_lt)])
        energy_prod = np.where(lt_mask, energy_prod, 0)

        # Storage costs and marginal costs (lifetime only)
        stor_cost = np.ones([len(titles['T2TI']), int(max_lt)])
        marg_stor_cost = np.ones([len(titles['T2TI']), int(max_lt)])

        if np.rint(data['MSAL'][r, 0, 0]) in [2]:
            stor_cost = stor_cost * (data['MSSP'][r, :, 0, np.newaxis] +
                                     data['MLSP'][r, :, 0, np.newaxis]) / 1000
            marg_stor_cost = marg_stor_cost * 0
        elif np.rint(data['MSAL'][r, 0, 0]) in [3, 4, 5]:
            stor_cost = stor_cost * (data['MSSP'][r, :, 0, np.newaxis] +
                                     data['MLSP'][r, :, 0, np.newaxis]) / 1000
            marg_stor_cost = marg_stor_cost * (data['MSSM'][r, :, 0, np.newaxis] +
                                          data['MLSM'][r, :, 0, np.newaxis]) / 1000
        else:
            stor_cost = stor_cost * 0
            marg_stor_cost = marg_stor_cost * 0

        stor_cost = np.where(lt_mask, stor_cost, 0)
        marg_stor_cost = np.where(lt_mask, marg_stor_cost, 0)
        
        dstor_cost = 0.2 * stor_cost         # Assume a standard deviation of 20%

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
        data['MWIC'][r, :, 0] = bcet[:, 2].copy()    # Investment cost component LCOE ($/kW)
        data['MWFC'][r, :, 0] = bcet[:, 4].copy()    # Fuel cost component of the LCOE ($/MWh)
        data['MCOC'][r, :, 0] = bcet[:, 0].copy()    # Carbon cost component of the LCOE ($/MWh)
        data['MCFC'][r, :, 0] = bcet[:, c2ti['11 Decision Load Factor']].copy() # The (marginal) capacity factor 

        # MWMC: FTT Marginal costs power generation ($/MWh)
        if np.rint(data['MSAL'][r, 0, 0]) > 1: # rint rounds to nearest int
            data['MWMC'][r, :, 0] = bcet[:, 0] + bcet[:, 4] + bcet[:, 6] + (data['MSSP'][r, :, 0] + data['MLSP'][r, :, 0])/1000
        else:
            data['MWMC'][r, :, 0] = bcet[:, 0] + bcet[:, 4] + bcet[:, 6]


        data['MMCD'][r, :, 0] = np.sqrt(bcet[:, 1] * bcet[:, 1] +
                                        bcet[:, 5] * bcet[:, 5] +
                                        bcet[:, 7] * bcet[:, 7])
        
        # Check if METC is nan
        if np.isnan(data['METC']).any():
            nan_indices_metc = np.where(np.isnan(data['METC']))
            raise ValueError(f"NaN values detected in lcoe ('metc') in  "
                             f"region {nan_indices_metc[0]} and technology {nan_indices_metc[1]}")

    return data
