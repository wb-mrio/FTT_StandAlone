# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 11:54:30 2024

@author: AE

=========================================
ftt_h_lcoh.py
=========================================
Domestic Heat FTT module.


This is the main file for FTT: Heat, which models technological
diffusion of domestic heat technologies due to consumer decision making. 
Consumers compare the **levelised cost of heat**, which leads to changes in the
market shares of different technologies.

The outputs of this module include levelised cost of heat technologies

Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Element-wise divide which replaces divide-by-zeros with zeros


Functions included:
    - get_lcoh
        Calculate levelised cost of transport
        
variables: 
cf = capacity factor
ce = conversion efficiency


"""

# Third party imports
import numpy as np

# Local library imports
from SourceCode.support.divide import divide

# %% LCOH
# --------------------------------------------------------------------------
# -------------------------- LCOH function ---------------------------------
# --------------------------------------------------------------------------

def get_lcoh(data, titles):
    """
    Calculate levelized costs.

    The function calculates the levelised cost of heat in 2014 Euros/kWh per
    boiler type. It includes intangible costs (gamma values) and together
    determines the investor preferences.
    """
    # Categories for the cost matrix (BHTC)
    c4ti = {category: index for index, category in enumerate(titles['C4TI'])}

    for r in range(len(titles['RTI'])):

        # Cost matrix
        #bhtc = data['BHTC'][r, :, :]

        # Boiler lifetime
        lt = data['BHTC'][r,:, c4ti['5 Lifetime']]
        max_lt = int(np.max(lt))
        lt_mat = np.linspace(np.zeros(len(titles['HTTI'])), max_lt-1,
                             num=max_lt, axis=1, endpoint=True)
        lt_max_mat = np.concatenate(int(max_lt)*[lt[:, np.newaxis]], axis=1)
        mask = lt_mat < lt_max_mat
        lt_mat = np.where(mask, lt_mat, 0)

        # Capacity factor
        cf = data['BHTC'][r,:, c4ti['13 Capacity factor mean'], np.newaxis]

        # Conversion efficiency
        ce = data['BHTC'][r,:, c4ti['9 Conversion efficiency'], np.newaxis]
        #print("ce:", ce)

        # Discount rate
        dr = data['BHTC'][r,:, c4ti['8 Discount rate'], np.newaxis]

        # Initialse the levelised cost components
        # Average investment cost
        it = np.zeros([len(titles['HTTI']), int(max_lt)])
        # print(it.shape)
        # print(data['BHTC'][r,:, c4ti['1 Investment cost mean']].shape)
        it[:, 0,np.newaxis] = data['BHTC'][r,:, c4ti['1 Inv cost mean (EUR/Kw)'],np.newaxis]/(cf*1000)


        # Standard deviation of investment cost
        dit = np.zeros([len(titles['HTTI']), int(max_lt)])
        dit[:, 0, np.newaxis] = divide(data['BHTC'][r,:, c4ti['2 Inv Cost SD'], np.newaxis], (cf*1000))

        # Upfront subsidy/tax at purchase time
        st = np.zeros([len(titles['HTTI']), int(max_lt)])
        st[:, 0, np.newaxis] = it[:, 0, np.newaxis] * data['HTVS'][r, :, 0, np.newaxis]

        # Average fuel costs
        ft = np.ones([len(titles['HTTI']), int(max_lt)])
        ft = ft * divide(data['BHTC'][r,:, c4ti['10 Fuel cost  (EUR/kWh)'], np.newaxis]*data['HEWP'][r, :, 0, np.newaxis], ce)
        ft = np.where(mask, ft, 0)

        # Standard deviation of fuel costs
        dft = np.ones([len(titles['HTTI']), int(max_lt)])
        dft = dft * ft * data['BHTC'][r,:, c4ti['11 Fuel cost SD'], np.newaxis] 
        dft = np.where(mask, dft, 0)
        
        # Fuel tax costs
        fft = np.ones([len(titles['HTTI']), int(max_lt)])
        fft = fft* divide(data['HTRT'][r, :, 0, np.newaxis], ce)
        fft = np.where(mask, fft, 0)
        #print("fft:", fft)
        #print(fft.shape)

        # Average operation & maintenance cost
        omt = np.ones([len(titles['HTTI']), int(max_lt)])
        omt = omt * divide(data['BHTC'][r,:, c4ti['3 O&M mean (EUR/kW)'], np.newaxis], (cf*1000))
        omt = np.where(mask, omt, 0)

        # Standard deviation of operation & maintenance cost
        domt = np.ones([len(titles['HTTI']), int(max_lt)])
        domt = domt * divide(data['BHTC'][r,:, c4ti['4 O&M SD'], np.newaxis], (cf*1000))
        domt = np.where(mask, domt, 0)

        # Feed-in-Tariffs
        fit = np.ones([len(titles['HTTI']), int(max_lt)])
        fit = fit * data['HEFI'][r, :, 0, np.newaxis]
        fit = np.where(mask, fit, 0)

        # Net present value calculations
        # Discount rate
        denominator = (1+dr)**lt_mat

        # 1-Expenses
        # 1.1-Without policy costs
        npv_expenses1 = (it+ft+omt)/denominator
        # 1.2-With policy costs
        npv_expenses2 = (it+st+ft+fft+omt-fit)/denominator
        # 1.3-Only policy costs
        npv_expenses3 = (st+fft-fit)/denominator
        # 2-Utility
        npv_utility = 1/denominator
        #Remove 1s for tech with small lifetime than max
        npv_utility[npv_utility==1] = 0
        npv_utility[:,0] = 1
        # 3-Standard deviation (propagation of error)
        npv_std = np.sqrt(dit**2 + dft**2 + domt**2)/denominator

        # 1-levelised cost variants in $/pkm
        # 1.1-Bare LCOH
        lcoh = np.sum(npv_expenses1, axis=1)/np.sum(npv_utility, axis=1)
        # 1.2-LCOH including policy costs
        tlcoh = np.sum(npv_expenses2, axis=1)/np.sum(npv_utility, axis=1)
        # 1.3-LCOH of policy costs
        lcoh_pol = np.sum(npv_expenses3, axis=1)/np.sum(npv_utility, axis=1)
        # Standard deviation of LCOH
        dlcoh = np.sum(npv_std, axis=1)/np.sum(npv_utility, axis=1)

        # LCOH augmented with non-pecuniary costs
        tlcohg = tlcoh + data['BHTC'][r, :, c4ti['12 Gamma value']]

        # Pay-back thresholds
        pb = data['BHTC'][r,:, c4ti['16 Payback time, mean']]
        dpb = data['BHTC'][r,:, c4ti['17 Payback time, SD']]

        # Marginal costs of existing units
        tmc = ft[:, 0] + omt[:, 0] + fft[:, 0] - fit[:, 0]
        dtmc = np.sqrt(dft[:, 0]**2 + domt[:, 0]**2)

        # Total pay-back costs of potential alternatives
        tpb = tmc + (it[:, 0] + st[:, 0])/pb
        dtpb = np.sqrt(dft[:, 0]**2 + domt[:, 0]**2 +
                       divide(dit[:, 0]**2, pb**2) +
                       divide(it[:, 0]**2, pb**4)*dpb**2)

        # Add gamma values
        tmc = tmc + data['BHTC'][r, :, c4ti['12 Gamma value']]
        tpb = tpb + data['BHTC'][r, :, c4ti['12 Gamma value']]

        # Pass to variables that are stored outside.
        data['HEWC'][r, :, 0] = lcoh            # The real bare LCOH without taxes
        data['HETC'][r, :, 0] = tlcoh           # The real bare LCOH with taxes
        data['HGC1'][r, :, 0] = tlcohg         # As seen by consumer (generalised cost)
        data['HWCD'][r, :, 0] = dlcoh          # Variation on the LCOH distribution
        data['HGC2'][r, :, 0] = tmc             # Total marginal costs
        data['HGD2'][r, :, 0] = dtmc          # SD of Total marginal costs
        data['HGC3'][r, :, 0] = tpb             # Total payback costs
        data['HGD3'][r, :, 0] = dtpb          # SD of Total payback costs

    return data