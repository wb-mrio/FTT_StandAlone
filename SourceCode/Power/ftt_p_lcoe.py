# -*- coding: utf-8 -*-
"""
=========================================
ftt_p_lcoe.py
=========================================
Power LCOE FTT module.
#################################

Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Bespoke element-wise divide which replaces divide-by-zeros with zeros

Functions included:
    - get_lcoe
        Calculate levelized costs

"""

# Standard library imports
from math import sqrt
import os
import copy
import sys
import warnings

# Third party imports
import pandas as pd
import numpy as np



# %% lcot
# -----------------------------------------------------------------------------
# --------------------------- LCOT function -----------------------------------
# -----------------------------------------------------------------------------
def get_lcoe(data, titles, scenario=None):
    """
    Calculate levelized costs.

    The function calculates the levelised cost of electricity in $2013/MWh. It includes
    intangible costs (gamma values) and determines the investor preferences.

    Parameters
    -----------
    data: dictionary
        Data is a container that holds all cross-sectional (of time) for all
        variables. Variable names are keys and the values are 3D NumPy arrays.
    titles: dictionary
        Titles is a container of all permissible dimension titles of the model.

    Returns
    ----------
    data: dictionary
        Data is a container that holds all cross-sectional (of time) data for
        all variables.
        Variable names are keys and the values are 3D NumPy arrays.
        The values inside the container are updated and returned to the main
        routine.

    Notes
    ---------
    Additional notes if required.
    """

    # Categories for the cost matrix (BCET)
    c2ti = {category: index for index, category in enumerate(titles['C2TI'])}
    
    

    global_south = ['26 Bulgaria (BG)', '32 Turkey (TR)', '33 Macedonia (MK)', '39 Russian Fed. (RS)', '41 China (CN)', '42 India (IN)', '43 Mexico (MX)', 
                    '44 Brazil (BR)', '45 Argentina (AR)', '46 Colombia (CO)', '47 Rest LatinAmerica(LA)', '50 Indonesia (ID)', '51 Rest of ASEAN (AS)', 
                    '52 Rest of OPEC ex Venez', '53 Rest of World (RW)', '54 Ukraine (UE)', '56 Nigeria (NG)', '57 South Africa (SA)', 
                    '58 NorthAfrica OPEC (ON)', '59 CentralAfricaOPEC(OC)', '60 Malaysia (MY)', '61 Kazakhstan (KZ)', '62 Rest NorthAfrica (AN)', 
                    '63 RestCentralAfrica(AC)', '64 Rest West Africa (AW)', '65 Rest East Africa (AE)', '66 Rest SouthAfrica (ZA)', '67 Egypt (EG)', 
                    '68 Dem. Rep. Congo (DC)', '69 Kenya (KE)']


    for r in range(len(titles['RTI'])):

        # Cost matrix
        bcet = data['BCET'][r, :, :]

        # plant lifetime
        lt = bcet[:, c2ti['9 Lifetime (years)']]
        bt = bcet[:, c2ti['10 Lead Time (years)']]
        max_lt = int(np.max(bt+lt))
        # max_bt = int(np.max(bt))
        full_lt_mat = np.linspace(np.zeros(len(titles['T2TI'])), max_lt-1,
                                  num=max_lt, axis=1, endpoint=True)
        lt_max_mat = np.concatenate(int(max_lt)*[(lt+bt-1)[:, np.newaxis]], axis=1)

        bt_max_mat = np.concatenate(int(max_lt)*[(bt-1)[:, np.newaxis]], axis=1)
        bt_mask = full_lt_mat <= bt_max_mat
        # bt_mat = np.where(bt_mask, full_lt_mat, 0)

        bt_mask_out = full_lt_mat > bt_max_mat
        lt_mask_in = full_lt_mat <= lt_max_mat
        lt_mask = np.where(lt_mask_in == bt_mask_out, True, False)
        # lt_mat = np.where(lt_mask, full_lt_mat, 0)

        # Capacity factor used in decisions (constant), not actual capacity factor
        # cf = bcet[:, c2ti['11 Decision Load Factor'], np.newaxis]
        # To match fortran, use actual CF
        # TODO: Is this correct?
        cf = data['MEWL'][r, :, 0]
        # Trap for very low CF
        cf[cf<0.000001] = 0.000001

        # Factor to transfer cost components in terms of capacity to generation
#        ones = np.ones([len(titles['T2TI']), 1])
        conv = 1/bt / cf/8766*1000

        # Discount rate
        # dr = bcet[6]
        dr = bcet[:, c2ti['17 Discount Rate (%)'], np.newaxis]

        # TT policies impact on discount rate (r), supposing a TT policy is implemented in 2022 in Global South countries 
        # (so fully implemented and functional in 2032, and the policy decreases r by 5% every year)
        def ttpolicy(dr, year):
            dr = dr*(1-0.05*(2050-year))  # updated only for renewables. Year is year of full implementation
            return dr
        new_dr = None
        if titles['RTI'][r] in global_south: 
        #and scenario and scenario=='S2':
            new_dr = ttpolicy(dr, 2032)

        if scenario:
            print(scenario)

        data['MWIC'][r, :, 0] = copy.deepcopy(bcet[:, c2ti['3 Investment ($/kW)']])
        data['MWFC'][r, :, 0] = copy.deepcopy(bcet[:, c2ti['5 Fuel ($/MWh)']])
        data['MCFC'][r, :, 0] = copy.deepcopy(bcet[:, c2ti['11 Decision Load Factor']])


        # Initialse the levelised cost components
        # Average investment cost
        it = np.ones([len(titles['T2TI']), int(max_lt)])
        it = it * bcet[:, c2ti['3 Investment ($/kW)'], np.newaxis] * conv[:, np.newaxis]
        it = np.where(bt_mask, it, 0)

        # Standard deviation of investment cost
        dit = np.ones([len(titles['T2TI']), int(max_lt)])
        dit = dit * bcet[:, c2ti['4 std ($/MWh)'], np.newaxis] * conv[:, np.newaxis]
        dit = np.where(bt_mask, dit, 0)

        # Subsidies
        st = np.ones([len(titles['T2TI']), int(max_lt)])
        st = (st * bcet[:, c2ti['3 Investment ($/kW)'], np.newaxis]
              * data['MEWT'][r, :, :] * conv[:, np.newaxis])
        st = np.where(bt_mask, st, 0)

        # Average fuel costs
        ft = np.ones([len(titles['T2TI']), int(max_lt)])
        ft = ft * bcet[:, c2ti['5 Fuel ($/MWh)'], np.newaxis]
        # TODO: Temporarily get MWFC from E3ME run
        ft2 = ft * data['MWFCX'][r, :, :]
        ft = np.where(lt_mask, ft, 0)

        # Standard deviation of fuel costs
        dft = np.ones([len(titles['T2TI']), int(max_lt)])
        dft = dft * bcet[:, c2ti['6 std ($/MWh)'], np.newaxis]
        dft = np.where(lt_mask, dft, 0)

        # fuel tax/subsidies
        # fft = np.ones([len(titles['T2TI']), int(max_lt)])
#        fft = ft * data['PG_FUELTAX'][r, :, :]
#        fft = np.where(lt_mask, ft, 0)

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

        # Energy production over the lifetime (incl. buildtime)
        # No generation during the buildtime, so no benefits
        et = np.ones([len(titles['T2TI']), int(max_lt)])
        et = np.where(lt_mask, et, 0)

        # Storage costs and marginal costs (lifetime only)
        stor_cost = np.ones([len(titles['T2TI']), int(max_lt)])
        marg_stor_cost = np.ones([len(titles['T2TI']), int(max_lt)])

        if np.rint(data['MSAL'][r, 0, 0]) == 1:
            stor_cost = stor_cost * (data['MSSP'][r, :, 0, np.newaxis] +
                                     data['MLSP'][r, :, 0, np.newaxis])/1000
            marg_stor_cost = marg_stor_cost * 0
        elif np.rint(data['MSAL'][r, 0, 0]) == 2 or np.rint(data['MSAL'][r, 0, 0]) == 3:
            stor_cost = stor_cost * (data['MSSP'][r, :, 0, np.newaxis] +
                                     data['MLSP'][r, :, 0, np.newaxis])/1000
            marg_stor_cost = marg_stor_cost * (data['MSSM'][r, :, 0, np.newaxis] +
                                          data['MLSM'][r, :, 0, np.newaxis])/1000
        else:
            stor_cost = stor_cost * 0
            marg_stor_cost = marg_stor_cost * 0

        stor_cost = np.where(lt_mask, stor_cost, 0)
        marg_stor_cost = np.where(lt_mask, marg_stor_cost, 0)

        # Net present value calculations
        # Discount rate
        denominator = (1+dr)**full_lt_mat if new_dr is None else (1+new_dr)**full_lt_mat

        # 1-Expenses
        # 1.1-Without policy costs
        npv_expenses1 = (it+ft+omt+stor_cost+marg_stor_cost)/denominator
        # 1.2-With policy costs
        # npv_expenses2 = (it+st+fft+ft+ct+omt+stor_cost+marg_stor_cost)/denominator
        npv_expenses2 = (it+st+ft+ct+omt+stor_cost+marg_stor_cost)/denominator
        # 1.3-Without policy, with co2p
        # TODO: marg_stor_cost?
        npv_expenses3 = (it+ft+ct+omt+stor_cost+marg_stor_cost)/denominator
        # 1.3-Only policy costs
        # npv_expenses3 = (ct+fft+st)/denominator
        # 2-Utility
        npv_utility = (et)/denominator
        #Remove 1s for tech with small lifetime than max
        npv_utility[npv_utility==1] = 0
        npv_utility[:,0] = 1
        # 3-Standard deviation (propagation of error)
        npv_std = np.sqrt(dit**2 + dft**2 + domt**2)/denominator

        # 1-levelised cost variants in $/pkm
        # 1.1-Bare LCOT
        lcoe = np.sum(npv_expenses1, axis=1)/np.sum(npv_utility, axis=1)
        # 1.2-LCOT including policy costs
        tlcoe = np.sum(npv_expenses2, axis=1)/np.sum(npv_utility, axis=1)+data['MEFI'][r, :, 0]
        # 1.3 LCOE excluding policy, including co2 price
        lcoeco2 = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)
        # 1.3-LCOT of policy costs
        # lcoe_pol = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)+data['MEFI'][r, :, 0]
        # Standard deviation of LCOT
        dlcoe = np.sum(npv_std, axis=1)/np.sum(npv_utility, axis=1)

        # LCOE augmented with gamma values
        tlcoeg = tlcoe+data['MGAM'][r, :, 0]

        # Pass to variables that are stored outside.
        data['MEWC'][r, :, 0] = copy.deepcopy(lcoe)     # The real bare LCOT without taxes
        data['MECW'][r, :, 0] = copy.deepcopy(lcoeco2)  # The real bare LCOE with taxes
        data['METC'][r, :, 0] = copy.deepcopy(tlcoeg)   # As seen by consumer (generalised cost)
        data['MTCD'][r, :, 0] = copy.deepcopy(dlcoe)    # Variation on the LCOT distribution

        # Output variables
        data['MWIC'][r, :, 0] = copy.deepcopy(bcet[:, 2])
        data['MWFC'][r, :, 0] = copy.deepcopy(bcet[:, 4])
        data['MCOC'][r, :, 0] = copy.deepcopy(bcet[:, 0])

#        data['MWMC'][r, :, 0] = bcet[:, 0] + bcet[:, 4] + bcet[:, 6]
        # TODO: Temporarily replace fuel costs with MWFCX
        data['MWMC'][r, :, 0] = bcet[:, 0] + data['MWFCX'][r, :, 0] + bcet[:, 6]

        data['MMCD'][r, :, 0] = np.sqrt(bcet[:, 1]*bcet[:, 1] +
                                        bcet[:, 5]*bcet[:, 5] +
                                        bcet[:, 7]*bcet[:, 7])

        if r == 40:
            x = 1+1

    return data

