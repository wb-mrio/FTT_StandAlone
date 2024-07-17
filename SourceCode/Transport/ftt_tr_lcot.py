# -*- coding: utf-8 -*-
"""
=========================================
ftt_tr_lcot.py
=========================================
Passenger road transport FTT module.
####################################

This is the main file for FTT: Transport, which models technological
diffusion of passenger vehicle types due to simulated consumer decision making.
Consumers compare the **levelised cost of heat**, which leads to changes in the
market shares of different technologies.

The outputs of this module include sales, fuel use, and emissions.

Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Bespoke element-wise divide which replaces divide-by-zeros with zeros
    - `estimation <econometrics_functions.html>`__
        Predict future values according to the estimated coefficients.

Functions included:
    - solve
        Main solution function for the module
    - get_lcot
        Calculate levelised cost of transport
        
variables: 
cf = capacity factor
ff = filling factors
ns = number of seats
      
        
"""
import numpy as np

# %% lcot
# -----------------------------------------------------------------------------
# --------------------------- LCOT function -----------------------------------
# -----------------------------------------------------------------------------
def get_lcot(data, titles, year):
    """
    Calculate levelized costs.

    The function calculates the levelised cost of transport in 2012$/p-km per
    vehicle type. It includes intangible costs (gamma values) and together
    determines the investor preferences.
    """

    # Categories for the cost matrix (BTTC)
    c3ti = {category: index for index, category in enumerate(titles['C3TI'])}

    # Taxable categories for fuel - not all fuels subject to fuel tax
    tf = np.ones([len(titles['VTTI']), 1])
    # Make vehicles that do not use petrol/diesel exempt
    tf[12:15] = 0   # CNG
    tf[18:21] = 0   # EVs
    tf[24:27] = 0   # Hydrogen
    taxable_fuels = np.zeros([len(titles['RTI']), len(titles['VTTI']), 1])

    for r in range(len(titles['RTI'])):

        # Cost matrix
        bttc = data['BTTC'][r, :, :]

        # Vehicle lifetime
        lt = bttc[:, c3ti['8 lifetime']]
        max_lt = int(np.max(lt))
        lt_mat = np.linspace(np.zeros(len(titles['VTTI'])), max_lt - 1,
                             num = max_lt, axis = 1, endpoint = True)
        lt_max_mat = np.concatenate(int(max_lt) * [lt[:, np.newaxis]], axis=1)
        mask = lt_mat < lt_max_mat
        lt_mat = np.where(mask, lt_mat, 0)

        # Capacity factor used in decisions (constant), not actual capacity factor
        cf = bttc[:, c3ti['12 Cap_F (Mpkm/kseats-y)'], np.newaxis]

        # Discount rate
        dr = bttc[:, c3ti['7 Discount rate'], np.newaxis]

        # Occupancy rates
        ff = bttc[:, c3ti['11 occupancy rate p/sea'], np.newaxis]

        # Number of seats
        ns = bttc[:, c3ti['15 Seats/Veh'], np.newaxis]

        # Energy use
        en = bttc[:, c3ti['9 energy use (MJ/km)'], np.newaxis]

        # Taxable fuels
        taxable_fuels[r,:] = tf[:]

        # Initialse the levelised cost components
        # Average investment cost
        it = np.zeros([len(titles['VTTI']), int(max_lt)])
        it[:, 0, np.newaxis] = bttc[:, c3ti['1 Prices cars (USD/veh)'],
                                     np.newaxis] / ns / ff / cf / 1000

        # Standard deviation of investment cost
        dit = np.zeros([len(titles['VTTI']), int(max_lt)])
        dit[:, 0, np.newaxis] = bttc[:, c3ti['2 Std of price'],
                                      np.newaxis] / ns / ff / cf / 1000

        # Vehicle tax at purchase
        vtt = np.zeros([len(titles['VTTI']), int(max_lt)])
        vtt[:, 0, np.newaxis] = (data['TTVT'][r, :, 0, np.newaxis] \
                                 + data['RTCO'][r, 0, 0] \
                                 * bttc[:,c3ti['14 CO2Emissions'], np.newaxis]) \
                                 / ns / ff / cf / 1000

        # Average fuel costs
        ft = np.ones([len(titles['VTTI']), int(max_lt)])
        ft = ft * bttc[:,c3ti['3 fuel cost (USD/km)'], np.newaxis] / ns / ff
        ft = np.where(mask, ft, 0)

        # Stadard deviation of fuel costs
        dft = np.ones([len(titles['VTTI']), int(max_lt)])
        dft = dft * bttc[:, c3ti['4 std fuel cost'], np.newaxis] / ns / ff
        dft = np.where(mask, dft, 0)

        # Fuel tax costs
        fft = np.ones([len(titles['VTTI']), int(max_lt)])
        fft = fft * data['RTFT'][r, :, 0, np.newaxis] * en / ns / ff \
              * taxable_fuels[r, :]
        fft = np.where(mask, fft, 0)
        
        # Average operation & maintenance cost
        omt = np.ones([len(titles['VTTI']), int(max_lt)])
        omt = omt * bttc[:, c3ti['5 O&M costs (USD/km)'], np.newaxis] / ns / ff
        omt = np.where(mask, omt, 0)

        # Standard deviation of operation & maintenance cost
        domt = np.ones([len(titles['VTTI']), int(max_lt)])
        domt = domt * bttc[:, c3ti['6 std O&M'], np.newaxis] / ns / ff
        domt = np.where(mask, domt, 0)

        # Road tax cost
        rtt = np.ones([len(titles['VTTI']), int(max_lt)])
        rtt = rtt * data['TTRT'][r, :, 0, np.newaxis] / cf / ns / ff / 1000
        rtt = np.where(mask, rtt, 0)

        # Vehicle price components for front end ($/veh)
        data["TWIC"][r, :, 0] = bttc[:, c3ti['1 Prices cars (USD/veh)']] \
                              + data["TTVT"][r, :, 0] + data["RTCO"][r, 0, 0] \
                              * bttc[:,c3ti['14 CO2Emissions']]
        
        # Fuel cost components for front end
        data["TWFC"][r, :, 0] = bttc[:,c3ti['3 fuel cost (USD/km)']] / ns[:,0] / ff[:,0] \
                                + data['RTFT'][r, 0, 0] * en[:,0] / ns[:,0] / ff[:,0] \
                                * taxable_fuels[r, :, 0]
        # Net present value calculations
        # Discount rate
        denominator = (1 + dr)**lt_mat

        # 1-Expenses
        # 1.1-Without policy costs
        npv_expenses1 = (it + ft + omt) / denominator
        # 1.2-With policy costs
        npv_expenses2 = (it + vtt + ft + fft + omt + rtt) / denominator
        # 1.3-Only policy costs
        npv_expenses3 = (vtt + fft + rtt) / denominator
        # 2-Utility
        npv_utility = 1/denominator
        #Remove 1s for tech with small lifetime than max
        npv_utility[npv_utility == 1] = 0
        npv_utility[:, 0] = 1
        # 3-Standard deviation (propagation of error)
        npv_std = np.sqrt(dit**2 + dft**2 + domt**2) / denominator

        # 1-levelised cost variants in $/pkm
        # 1.1-Bare LCOT
        lcot = np.sum(npv_expenses1, axis = 1) / np.sum(npv_utility, axis = 1)
        # 1.2-LCOT including policy costs
        tlcot = np.sum(npv_expenses2, axis = 1) / np.sum(npv_utility, axis = 1)
        # 1.3-LCOT of policy costs
        lcot_pol = np.sum(npv_expenses3, axis = 1) \
                   / np.sum(npv_utility, axis = 1)
        # Standard deviation of LCOT
        dlcot = np.sum(npv_std, axis = 1) / np.sum(npv_utility, axis = 1)

        # LCOT augmented with non-pecuniary costs
        tlcotg = tlcot * (1 + data['TGAM'][r, :, 0])

        # Transform into lognormal space
        logtlcot = np.log(tlcot * tlcot / np.sqrt(dlcot * dlcot + tlcot * tlcot)) \
                   + data['TGAM'][r, :, 0]
        dlogtlcot = np.sqrt(np.log(1.0 + dlcot * dlcot / (tlcot * tlcot)))

        # Pass to variables that are stored outside.
        data['TEWC'][r, :, 0] = lcot           # The real bare LCOT without taxes
        data['TETC'][r, :, 0] = tlcot          # The real bare LCOE with taxes
        data['TEGC'][r, :, 0] = tlcotg         # As seen by consumer (generalised cost)
        data['TELC'][r, :, 0] = logtlcot       # In lognormal space
        data['TECD'][r, :, 0] = dlcot          # Variation on the LCOT distribution
        data['TLCD'][r, :, 0] = dlogtlcot      # Log variation on the LCOT distribution

    return data