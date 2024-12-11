# -*- coding: utf-8 -*-
"""
=========================================
ftt_fr_lcof.py
=========================================
Freight LCOF FTT module.
########################


Functions included:
    - get_lcof
        Calculate levelized costs

"""

# Third party imports
import numpy as np


def get_lcof(data, titles):
    """
    Calculate levelized costs.

    The function calculates the levelised cost of freight transport in 2012$/t-km per
    vehicle type. These costs are then converted into 2010 Euros/t-km per vehicle type.
    It includes intangible costs (gamma values) and together
    determines the investor preferences.

    Parameters
    -----------
    data: dictionary
        Data is a dictionary with the data of the current year for all variables.
        variables. Variable names are keys and the values are 3D NumPy arrays.
    titles: dictionary
        Titles is a container of all permissible dimension titles of the model.

    Returns
    ----------
    data: dictionary
        Data is a dictionary with the data of the current year for all variables.
        Variable names are keys and the values are 3D NumPy arrays.
        The values inside the container are updated and returned to the main
        routine.

    Notes
    ---------
    Additional notes if required.
    """
    # Categories for the cost matrix (BZTC)
    c6ti = {category: index for index, category in enumerate(titles['C6TI'])}

    # Taxable categories for fuel - not all fuels subject to fuel tax
    tf = np.ones([len(titles['FTTI']), 1])
    # Make vehicles that do not use petrol/diesel exempt
    tf[20:45] = 0   # CNG, PHEV, BEV, bio-ethanol, FCEV

    taxable_fuels = np.zeros([len(titles['RTI']), len(titles['FTTI']), 1])

    for r in range(len(titles['RTI'])):

        # Defining and Initialising Variables

        #Cost matrix
        BZTC = data['BZTC'][r, :, :]

        #First, mask for lifetime
        LF = BZTC[:, c6ti['8 Lifetime (y)']]
        max_LF = int(np.max(LF))
        LF_mat = np.linspace(np.zeros(len(titles['FTTI'])), max_LF-1,
                             num=max_LF, axis=1, endpoint=True)
        LF_max_mat = np.concatenate(int(max_LF) * [LF[:, np.newaxis]], axis=1)
        mask = LF_mat < LF_max_mat
        LF_mask = np.where(mask, LF_mat, 0)

        # Taxable fuels
        taxable_fuels[r,:] = tf[:]

        # Discount rate
        rM = BZTC[:,c6ti['7 Discount rate'], np.newaxis]
        # For NPV calculations
        denominator = (1+rM)**LF_mat


        # Costs of trucks, paid once in a lifetime
        It = np.ones([len(titles['FTTI']), int(max_LF)])
        It = It * BZTC[:, c6ti['1 Purchase cost (USD/veh)'], np.newaxis]
        It = It / BZTC[:, c6ti['17 Average mileage (km/y)'], np.newaxis]
        It[:,1:] = 0

        # Standard deviation of costs of trucks
        dIt = np.ones([len(titles['FTTI']), int(max_LF)])
        dIt = dIt * BZTC[:, c6ti['2 Std of purchase cost'], np.newaxis]
        dIt = dIt / BZTC[:, c6ti['17 Average mileage (km/y)'], np.newaxis]
        dIt[:,1:] = 0

        # Reg tax based on carbon price, RTCOt = ($/tCO2/km)/(tCO2/km)
        RZCOt = np.ones([len(titles['FTTI']), int(max_LF)])
        RZCOt = (RZCOt * BZTC[:, c6ti['13 CO2 emissions (gCO2/km)'], np.newaxis]
              * data['RZCO'][r,0,0])
        RZCOt[:,1:] = 0

        # Registration Taxes, ZTVT is vehicle tax
        ItVT = np.ones([len(titles['FTTI']), int(max_LF)])
        ItVT = ItVT * data['ZTVT'][r,:,0, np.newaxis]
        ItVT = ItVT / BZTC[:, c6ti['17 Average mileage (km/y)'], np.newaxis]
        ItVT[:,1:] = 0

        # Fuel Cost
        FT = np.ones([len(titles['FTTI']), int(max_LF)])
        FT = FT * BZTC[:, c6ti['3 fuel cost (USD/km)'], np.newaxis]
        FT = np.where(mask, FT, 0)

        # Standard deviation of fuel costs
        dFT = np.ones([len(titles['FTTI']), int(max_LF)])
        dFT = dFT * BZTC[:, c6ti['4 std fuel cost'], np.newaxis]
        dFT = np.where(mask, dFT, 0)

       # fuel tax/subsidies
        fft = np.ones([len(titles['FTTI']), int(max_LF)])
        fft = fft * data['RZFT'][r, :, 0, np.newaxis] \
              * BZTC[:, c6ti["9 Energy use (MJ/vkm)"], np.newaxis] \
              * taxable_fuels[r, :]
        fft = np.where(mask, fft, 0)

        # O&M costs
        OMt = np.ones([len(titles['FTTI']), int(max_LF)])
        OMt = OMt * BZTC[:, c6ti['5 O&M costs (USD/km)'], np.newaxis]
        OMt = np.where(mask, OMt, 0)

        # Standard deviation of O&M costs
        dOMt = np.ones([len(titles['FTTI']), int(max_LF)])
        dOMt = dOMt * BZTC[:, c6ti['6 std O&M'], np.newaxis]
        dOMt = np.where(mask, dOMt, 0)

        # Capacity factors
        Lfactor = np.ones([len(titles['FTTI']), int(max_LF)])
        Lfactor = Lfactor * BZTC[:, c6ti['10 Loads (t or passengers/veh)'], np.newaxis]

        # Road Tax
        RT = np.ones([len(titles['FTTI']), int(max_LF)])
        RT = RT * data['ZTRT'][r, :, 0, np.newaxis]
        RT = np.where(mask, RT, 0)
        
        # Calculate LCOF without policy, and find standard deviation
        npv_expenses1 = (It+FT+OMt)/Lfactor
        npv_expenses1 = (npv_expenses1/denominator)
        npv_utility = 1/denominator
        
        # Remove 1s for tech with small lifetime than max
        npv_utility[npv_utility==1] = 0
        npv_utility[:,0] = 1
        LCOF = np.sum(npv_expenses1, axis =1)/np.sum(npv_utility, axis=1)

        dnpv_expenses1 = np.sqrt(((dIt**2)/(Lfactor**2)) + ((dFT**2)/(Lfactor**2))
        + ((dOMt**2)/(Lfactor**2)))/denominator
        dLCOF = np.sum(dnpv_expenses1, axis=1)/np.sum(npv_utility, axis=1)

        # Calculate LCOF with policy, and find standard deviation
        npv_expenses2 = (It+ItVT+FT+fft+OMt+RT)/Lfactor
        npv_expenses2 = npv_expenses2/denominator
        TLCOF = np.sum(npv_expenses2, axis=1)/np.sum(npv_utility, axis=1)
        dTLCOF=dLCOF

        # Introduce Gamma Values
        TLCOFG = TLCOF * (1 + data['ZGAM'][r, :, 0])

        # Convert costs into logarithmic space - applying a log-normal distribution
        LTLCOF = np.log10((TLCOF**2)/np.sqrt((dTLCOF**2)+(TLCOF**2))) + data['ZGAM'][r, :, 0]

        dLTLCOF = np.sqrt(np.log10(1+(dTLCOF**2)/(TLCOF**2)))

        data['ZTLC'][r, :, 0] = LCOF        # LCOF without policy
        data['ZTLD'][r, :, 0] = dLCOF       # LCOF without policy SD
        data['ZTTC'][r, :, 0] = TLCOF       # LCOF with policy
        data['ZTTD'][r, :, 0] = dTLCOF      # LCOF with policy SD
        data['ZEGC'][r, :, 0] = TLCOFG      # LCOF with policy and gamma
        data['ZTLL'][r, :, 0] = LTLCOF      # LCOF log space with policy and gamma
        data['ZTDD'][r, :, 0] = dLTLCOF     # LCOF log space with policy SD
        
        # Vehicle price components for front end ($/veh)
        data["ZWIC"][r, :, 0] = BZTC[:, c6ti['1 Purchase cost (USD/veh)']] \
                                + data["ZTVT"][r, :, 0] \
                                + BZTC[:, c6ti["13 CO2 emissions (gCO2/km)"]] \
                                * data["RZCO"][r, 0, 0]
        
        # Vehicle fuel price components for front end ($/km)
        data["ZWFC"][r, :, 0] = BZTC[:, c6ti["3 fuel cost (USD/km)"]] \
                                + data['RZFT'][r, 0, 0] \
                                * BZTC[:, c6ti["9 Energy use (MJ/vkm)"]] \
                                * taxable_fuels[r, :, 0]
    return data
