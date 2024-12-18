# -*- coding: utf-8 -*-
"""
=========================================
ftt_p_rldc.py
=========================================
Power generation RLDC FTT module.


Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Element-wise divide which replaces divide-by-zeros with zeros

Functions included:
    - rldc
        Calculate residual load duration curves
"""

# Third party imports
import pandas as pd
import numpy as np

# Local library imports
from SourceCode.support.divide import divide

#%% FEQS
def feqs(a):
    return np.maximum(a, 1e-3)

# %% rldc function
# -----------------------------------------------------------------------------
# -------------------------- RLDC calcultion ------------------------------
# -----------------------------------------------------------------------------
def rldc(data, MEWDt, time_lag, data_dt, year, titles, histend):
    """
    Calculate RLDCs.

    The function calculates the RLDCs and returns load band heights, curtailment,
    and storage information, including storage costs and marginal costs
    for wind and solar.

    Parameters
    -----------
    data: dictionary
        data is a dictionary with data of current year.
        Variable names are keys and the values are 3D NumPy arrays.
    time_lag: dictionary
        time_lag is the same, but with data for last year.
        Variable names are keys and the values are 3D NumPy arrays.
    titles: dictionary
        Titles is a container of all permissible dimension titles of the model.

    Returns
    ----------
    data: dictionary
    Updated variables are MCRT (curtailment), MCTG (gross curtailment per tech),
    MKLB (capacity by load band), 
    Four categories of storage costs (long-term vs short-term, normal vs marginal)
    

    """
    
    # This is computed in a separate python file, using the centroid from the geopandas package
    latitude = np.asarray([50.6, 64.0, 51.0, 39.0, 40.3, 39.6, 53.2, 42.6, 49.8, 52.3,
                           47.6, 39.6, 64.1, 62.2, 53.7, 49.8, 58.6, 35.1, 56.8, 55.3,
                           47.2, 35.9, 52.1, 46.1, 48.7, 42.7, 45.8, 65.6, 46.8, 65.0,
                           45.0, 39.0, 41.6, 42.1, 37.4, 57.6, 25.3, 41.4, 59.6, 53.5,
                           35.6, 22.6, 23.7, 10.4, 34.4, 3.9,  15.6, 36.4, 23.7, 2.2,
                           14.3, 24.5, 32.3, 49.1, 24.0, 9.5,  28.8, 27.4, 3.8,  3.7,
                           47.9, 24.8, 9.1,  11.2, 9.0, 20.6, 26.4, 2.8 , 0.6, 23.9,
                           29.8])
    seasonality_index = latitude/60 # Used to divide the capacity constraint between long and short-term storage needs
    seasonality_index[seasonality_index > 1.0] = 1.0

    # Mapping of NWR = 53 world regions to 8 available RLDC regions:
    # 0 = Europe, 1 = Latin America, 2 = India, 3 = USA, 4 = Japan, 5 = Middle
    # East and North Africa, 6 = Sub-Saharan Africa, 7 = China
    rldc_regmap = np.zeros(len(titles['RTI']), dtype=int)
    rldc_regmap[0:33] = 0 # Europe
    rldc_regmap[33] = 3 # USA
    rldc_regmap[34] = 4 # Japan
    rldc_regmap[35:38] = 3 # Canada, Australia, New Zealand (USA as proxy)
    rldc_regmap[38:40] = 0  # Russia, Rest of Annex I (Europe as proxy)
    rldc_regmap[40] = 7  # China
    rldc_regmap[41] = 2  # India
    rldc_regmap[42:47] = 1  # Mexico, Brazil, Argentina, Colombia, Rest of LAM
    rldc_regmap[47:49] = 4  # Korea, Taiwan (Japan as proxy)
    rldc_regmap[49:51] = 2  # Indonesia, Rest of ASEAN (India as proxy)
    rldc_regmap[51] = 5  # OPEC excluding Venezuela (MENA as proxy)
    rldc_regmap[52] = 6  # Rest of the world (Sub-Saharan Africa as proxy)
    rldc_regmap[53] = 0  # Ukraine (Europe as proxy)
    rldc_regmap[54] = 5  # Saudi (MENA as proxy)
    rldc_regmap[55:57] = 6  # Nigeria, South Africa, Rest Africa (Africa as proxy)
    rldc_regmap[57:59] = 5  # Africa OPEC (MENA as proxy)
    rldc_regmap[59:61] = 2  # Malaysia,Kazakhstan (India as proxy)
    rldc_regmap[61:69] = 6  # Rest of African regions (Africa as proxy)
    rldc_regmap[69] = 5  # UAE (MENA as proxy)
    rldc_regmap[70] = 5  # Pakistan (MENA as proxy)

    # Define matrices with polynomial coefficients for 8 RLDC regions
    # 10 input parameters (shares of generation of wind and solar in a
    # polynomial 1 + Sw + Ss + Sw^2 + Sw*Ss + Ss^2 + Sw^3 + Sw^2*Ss + Sw*Ss^2 + Ss^3)
    # 8 output results (Curtailment, storage capacity, storage costs, 5 load
    # band heights in order H4, H3, H2, H1, Hp)
    rldc_coeff = np.empty((8,10,8))

    # Europe (RLDCreg = 0)
    rldc_coeff[0] = np.array([[0.000, 0.000, 0.000, 1.301, 1.175, 1.058, 0.871, 1.386],
                             [0.048, 0.000, 0.000,-1.066,-1.189,-1.013,-1.138,-0.588],
                             [0.017, 0.000, 0.000,-0.467,-0.806,-0.756,-1.729,-0.483],
                             [-0.220, 0.039, 0.038, 0.602, 0.783, 0.124, 0.064, 0.013],
                             [-0.191, 0.513,-0.008,-0.585, 0.402,-0.588, 1.359,-0.662],
                             [-0.046, 1.435, 1.157,-0.171, 1.013, 0.004, 1.135,-0.397],
                             [0.336,-0.020,-0.018,-0.172,-0.302, 0.024, 0.151, 0.079],
                             [0.556, 0.000, 0.163,-0.223,-0.993, 0.341,-0.281, 0.000],
                             [0.191,-0.197, 0.731, 0.346,-0.657, 0.108,-0.476, 0.255],
                             [0.309,-0.736,-0.593, 0.158,-0.578, 0.112,-0.244, 0.299]])

    # Latin America (RLDCreg = 1)
    rldc_coeff[1] = np.array([[0.000, 0.000, 0.000, 1.224, 1.160, 1.080, 0.875, 1.312],
                             [0.005, 0.000, 0.000,-0.707,-0.962,-1.014,-1.308,-0.627],
                             [0.002, 0.000, 0.000,-0.142,-0.219,-0.712,-1.893,-0.377],
                             [-0.064, 0.106, 0.026, 0.094, 0.530, 0.260, 0.367, 0.286],
                             [-0.059, 0.642, 0.599,-1.118,-0.615,-0.822, 1.703,-0.678],
                             [0.112, 1.293, 0.743,-0.615,-0.316, 0.106, 1.441,-0.593],
                             [0.247, 0.003, 0.059, 0.018,-0.257,-0.096, 0.041,-0.133],
                             [0.393,-0.379,-0.283, 0.252,-0.261, 0.346,-0.418, 0.293],
                             [0.159, 0.109, 0.403, 0.576, 0.438, 0.429,-0.638, 0.265],
                             [0.062,-0.366, 0.143, 0.162,-0.023,-0.140,-0.367, 0.278]])

    # India (RLDCreg = 2)
    rldc_coeff[2] = np.array([[0.000, 0.000, 0.000, 1.111, 1.060, 1.020, 0.960, 1.182],
                             [0.002, 0.059, 0.016,-0.614,-0.685,-0.872,-1.749,-0.517],
                             [0.002, 0.000, 0.000,-0.064,-0.085,-0.382,-2.195,-0.127],
                             [0.190,-0.056,-0.011, 0.616, 0.665, 0.705, 1.020, 0.484],
                             [-0.052, 0.368, 0.493,-0.808,-1.068,-1.165, 2.389,-0.296],
                             [0.052, 1.779, 1.008,-0.574,-0.323,-0.117, 1.791,-0.833],
                             [0.150, 0.118, 0.002,-0.292,-0.357,-0.373,-0.205,-0.195],
                             [0.306, 0.024,-0.085, 0.016,-0.045,-0.020,-0.636,-0.140],
                             [0.301,-0.311,-0.209, 0.611, 0.836, 0.836,-1.001, 0.348],
                             [0.161,-0.807,-0.051, 0.102,-0.086,-0.116,-0.487, 0.343]])

    # USA (RLDCreg = 3)
    rldc_coeff[3] = np.array([[0.000, 0.000, 0.000, 1.381, 1.176, 1.029, 0.872, 1.544],
                             [0.018, 0.001, 0.000,-0.838,-0.949,-0.957,-1.280,-0.687],
                             [0.006, 0.000, 0.000,-1.558,-0.881,-0.555,-1.601,-1.934],
                             [-0.119, 0.029, 0.036, 0.492, 0.420, 0.100, 0.238, 0.330],
                             [-0.112, 0.490, 0.235,-1.032,-0.190,-0.644, 1.588,-0.822],
                             [0.052, 1.314, 0.819, 1.853, 0.924,-0.219, 0.915, 2.325],
                             [0.263, 0.026,-0.012,-0.257,-0.206,-0.001, 0.109,-0.186],
                             [0.532,-0.314,-0.181, 0.477,-0.084, 0.358,-0.425, 0.317],
                             [0.175, 0.128, 0.506, 0.351,-0.287, 0.195,-0.527, 0.454],
                             [0.153,-0.674,-0.233,-0.963,-0.574, 0.138,-0.159,-1.148]])

    # Japan (RLDCreg = 4)
    rldc_coeff[4] = np.array([[0.000, 0.000, 0.000, 1.275, 1.147, 1.045, 0.891, 1.429],
                             [0.001, 0.000, 0.000,-0.802,-0.985,-1.030,-1.462,-0.514],
                             [0.000, 0.226, 0.000,-0.719,-0.419,-0.565,-1.813,-1.172],
                             [-0.036, 0.067, 0.037, 0.592, 0.856, 0.633, 0.607, 0.337],
                             [-0.007, 0.800, 0.853,-1.065,-0.622,-0.797, 1.854,-1.125],
                             [0.280, 0.971, 1.225, 0.369, 0.143, 0.040, 1.309, 0.901],
                             [0.330,-0.034,-0.014,-0.236,-0.397,-0.311,-0.051,-0.121],
                             [0.135, 0.000, 0.000, 0.395,-0.163, 0.031,-0.474, 0.093],
                             [0.009,-0.308,-0.328, 0.302, 0.053, 0.259,-0.670, 0.471],
                             [0.041,-0.542,-0.628,-0.107,-0.093, 0.033,-0.315,-0.287]])

    # Middle East and North Africa (RLDCreg = 5)
    rldc_coeff[5] = np.array([[0.000, 0.000, 0.000, 1.217, 1.154, 1.073, 0.885, 1.283],
                             [0.050, 0.084, 0.010,-0.997,-1.058,-1.045,-1.133,-0.795],
                             [0.050, 0.000, 0.000,-0.136,-0.387,-1.202,-1.779,-0.312],
                             [-0.185,-0.125, 0.003, 0.362, 0.252, 0.113, 0.066, 0.231],
                             [-0.351, 0.409, 0.339,-0.530,-0.661,-0.293, 1.542,-0.436],
                             [-0.206, 1.571, 0.930,-0.807,-0.276, 1.335, 1.189,-0.743],
                             [0.229, 0.062, 0.009,-0.109,-0.055,-0.004, 0.136,-0.039],
                             [0.650,-0.133,-0.185,-0.296,-0.118, 0.304,-0.294, 0.000],
                             [0.621,-0.091, 0.083, 0.448, 0.553, 0.073,-0.561, 0.168],
                             [0.367,-0.806,-0.227, 0.374, 0.058,-0.799,-0.260, 0.442]])

    # Sub-Saharan Africa (RLDCreg = 6);
    rldc_coeff[6] = np.array([[0.000, 0.000, 0.000, 1.165, 1.093, 1.043, 0.929, 1.225],
                             [0.050, 0.023, 0.000,-0.977,-0.979,-1.065,-1.206,-0.977],
                             [0.044, 0.000, 0.000, 0.000,-0.137,-0.703,-2.062,-0.084],
                             [-0.196,-0.031, 0.038, 0.409, 0.284, 0.265, 0.100, 0.742],
                             [-0.344, 0.547, 0.384,-0.714,-0.814,-0.592, 1.817,-0.426],
                             [-0.141, 1.619, 0.803,-0.827,-0.426, 0.344, 1.557,-0.985],
                             [0.258, 0.014,-0.018,-0.106,-0.077,-0.096, 0.143,-0.273],
                             [0.681,-0.019,-0.184,-0.058,-0.084, 0.206,-0.399,-0.294],
                             [0.598,-0.392, 0.239, 0.586, 0.713, 0.555,-0.688, 0.478],
                             [0.266,-0.579, 0.172, 0.236, 0.007,-0.336,-0.392, 0.410]])

    # China (RLDCreg = 7);
    rldc_coeff[7] = np.array([[0.000, 0.000, 0.000, 1.176, 1.131, 1.037, 0.908, 1.201],
                             [0.008, 0.109, 0.000,-0.778,-0.921,-0.855,-1.039,-0.447],
                             [0.004, 0.000, 0.000,-0.470,-0.658,-0.629,-1.881,-0.550],
                             [-0.073,-0.060, 0.067, 0.205, 0.313,-0.045,-0.157, 0.055],
                             [-0.087, 0.588, 0.725,-0.674,-0.052,-0.757, 1.434,-0.875],
                             [0.073, 1.571, 1.093, 0.019, 0.680, 0.239, 1.282, 0.076],
                             [0.211, 0.009,-0.034,-0.034,-0.133, 0.054, 0.233,-0.007],
                             [0.426, 0.000,-0.177,-0.107,-0.412, 0.259,-0.273, 0.189],
                             [0.252,-0.226,-0.066, 0.471,-0.200, 0.349,-0.489, 0.339],
                             [0.191,-0.806,-0.434,-0.023,-0.491,-0.174,-0.291, 0.005]])
    
    # Electricity demand (!= same as supply!)
    e_dem = MEWDt / 3.6 * 1000
    
    # Apply learning-by-doing on storage techs
    learning_exp_ss = -0.2945 # = -(0.421 + 0.168)/2: average for flow and li-ion batteries, and mid-length storage may be included here.
    learning_exp_ls = -0.129  # Both from Way paper (https://www.inet.ox.ac.uk/files/energy_transition_paper-INET-working-paper.pdf), latter less reliable due to data constraints
    
    

    # Wind and solar shares for all regions
    Sw = np.zeros(len(titles['RTI']))
    Ss = np.zeros(len(titles['RTI']))
    Sw = np.divide(np.sum(data['MEWG'][:, [16, 17], 0], axis=1),
                   e_dem[:],
                   where=~np.isclose(e_dem[:], 0.0))
    Ss = np.divide(data['MEWG'][:, 18, 0],
                   e_dem[:],
                   where=~np.isclose(e_dem[:], 0.0))

    # Format matrix including Sw and Ss powers and cross terms
    # template: [1 Sw Ss Sw^2 Sw*Ss Ss^2 Sw^3 Sw^2*Ss Sw*Ss^2 Ss^3]
    vre_powers = np.array([np.ones(len(Sw)), Sw, Ss, Sw**2, np.multiply(Sw, Ss), Ss**2, Sw**3, np.multiply(Sw**2, Ss), np.multiply(Sw, Ss**2), Ss**3])
    vre_powers = vre_powers.transpose()
    
    # Different configurations of vre_powers to estimate splits between solar
    # and wind
    vre_gr_sol = 0.005 * np.ones(len(titles['RTI']))
    vre_gr_sol = np.maximum((divide(data['MEWS'][:, 18, 0] * data['MEWL'][:, 18, 0],
                               time_lag['MEWS'][:, 18, 0] * time_lag['MEWL'][:, 18, 0])
                               - 1.0) * data['MEWS'][:, 18, 0],
                                0.005)
    
    vre_ggr_sol = 0.002 * data['MEWG'][:, 18, 0]
    vre_ggr_sol = np.maximum((divide(data['MEWS'][:, 18, 0] * data['MEWL'][:, 18, 0],
                                 time_lag['MEWS'][:, 18, 0] * time_lag['MEWL'][:, 18, 0])
                                 -1.0)*data['MEWG'][:, 18, 0],
                                 0.002 * data['MEWG'][:, 18, 0])
    
    vre_gr_wind = 0.005 * np.ones(len(titles['RTI']))
    vre_gr_wind = np.maximum((divide(np.sum(data['MEWS'][:, [16, 17], 0] * data['MEWL'][:, [16, 17], 0], axis=1),
                                 np.sum(time_lag['MEWS'][:, [16, 17], 0] * time_lag['MEWL'][:, [16, 17], 0], axis=1))
                                 -1.0)*np.sum(data['MEWS'][:, [16,17], 0], axis=1),
                                 0.005)
    
    vre_ggr_wind = 0.002 * np.sum(data['MEWG'][:, [17,18], 0], axis=1)
    vre_ggr_wind = np.maximum((divide(np.sum(data['MEWS'][:, [16, 17], 0] * data['MEWL'][:, [16, 17], 0], axis=1),
                                 np.sum(time_lag['MEWS'][:, [16, 17], 0] * time_lag['MEWL'][:, [16, 17], 0], axis=1))
                                 -1.0)*np.sum(data['MEWG'][:, [16,17], 0], axis=1),
                                 0.002 * np.sum(data['MEWG'][:, [17,18], 0], axis=1))
    

    # What is the impact of additional solar
    Ss2 = np.add(Ss, vre_gr_sol)
    vre_powers_solar = np.array([np.ones(len(Sw)), Sw, Ss2, Sw**2, np.multiply(Sw, Ss2), Ss2**2, Sw**3, np.multiply(Sw**2, Ss2), np.multiply(Sw, Ss2**2), Ss2**3])
    vre_powers_solar = vre_powers_solar.transpose()
    
    # What is the impact of additional wind
    Sw2 = np.add(Sw, vre_gr_wind)
    vre_powers_wind = np.array([np.ones(len(Sw2)), Sw2, Ss, Sw2**2, np.multiply(Sw2, Ss), Ss**2, Sw2**3, np.multiply(Sw2**2, Ss), np.multiply(Sw2, Ss**2), Ss**3])
    vre_powers_wind = vre_powers_wind.transpose()

    # What is the impact of only solar
    vre_powers_split_sol = np.array([np.ones(len(Ss)), np.zeros(len(Ss)), Ss, np.zeros(len(Ss)), np.zeros(len(Ss)), Ss**2, np.zeros(len(Ss)), np.zeros(len(Ss)), np.zeros(len(Ss)), Ss**3])
    vre_powers_split_sol = vre_powers_split_sol.transpose()    
    
    # What is the impact of only wind
    vre_powers_split_wind = np.array([np.ones(len(Sw)), Sw, np.zeros(len(Sw)), Sw**2, np.zeros(len(Sw)), np.zeros(len(Sw)), Sw**3, np.zeros(len(Sw)), np.zeros(len(Sw)), np.zeros(len(Sw))])
    vre_powers_split_wind = vre_powers_split_wind.transpose()  
    
    # Initialise the ratio needed to determine the split responsibilities
    ratio = np.ones(len(titles["RTI"]))
    ratio_ls = np.ones(len(titles["RTI"]))
    ratio_ss = np.ones(len(titles["RTI"]))
    curt_w = np.zeros(len(titles["RTI"]))
    curt_s = np.zeros(len(titles["RTI"]))
    
    # Bool to indicate which tech is VRE and which is not
    Svar = data['MWDD'][0, :, 5]
    Snotvar = 1 - data['MWDD'][0, :, 5]

    for r in range(len(titles['RTI'])):
        if Sw[r] + Ss[r] == 0:
            print(f"No wind or solar in region {r}")
            

        # SHORT-TERM STORAGE
        # Multidimensional polynomial from Ueckerdt et al. (2017)
        # Gives [Curt, Ustor, CostStor, H4, H3, H3, H1, Hp]
        # 8 output results (Curtailment, storage capacity, storage costs, 5 load band heights in order H4, H3, H2, H1, Hp)
        rldc_prod = np.dot(vre_powers[r], rldc_coeff[rldc_regmap[r]])
        # RLDC parameters due to slightly more wind or solar
        rldc_prod_wind = np.dot(vre_powers_wind[r], rldc_coeff[rldc_regmap[r]])
        rldc_prod_solar = np.dot(vre_powers_solar[r], rldc_coeff[rldc_regmap[r]])
        # RLDC parameters due to exclusively wind or solar
        rldc_prod_split_wind = np.dot(vre_powers_split_wind[r], rldc_coeff[rldc_regmap[r]])
        rldc_prod_split_sol = np.dot(vre_powers_split_sol[r], rldc_coeff[rldc_regmap[r]])
         
        # Estimate geometric mean of the ratio based on wind/sol excl. and the ratio of marg. wind/sol
        ratio[r] = np.sqrt(feqs(rldc_prod_split_wind[0]) / feqs(rldc_prod_split_sol[0]) * 
                             feqs(feqs(rldc_prod[0]) - feqs(rldc_prod_split_sol[0])) /
                             feqs(feqs(rldc_prod[0]) - feqs(rldc_prod_split_wind[0]))) 
                
       
        # Estimate general curtailment rate and the splits for wind and solar
        data['MCRT'][r, 0, 0] = rldc_prod[0]
        if Sw[r] != 0 and Ss[r] != 0: 
            curt_w[r] = data['MCRT'][r, 0, 0] * (Sw[r] + Ss[r]) / (Sw[r] + Ss[r]/ratio[r])
            curt_s[r] = data['MCRT'][r, 0, 0] * (Sw[r] + Ss[r]) / (Sw[r]*ratio[r] + Ss[r])
        
        # Upper limit of values
        if data['MCRT'][r, 0, 0] > 0.75: data['MCRT'][r, 0, 0] = 0.75
        if curt_w[r] > 0.75: curt_w[r] = 0.75
        if curt_s[r] > 0.75: curt_s[r] = 0.75
        
        # Gross curtailment ratio by technology
        # Note that some curtailed electricity is used to charge storage techs
        data['MCTG'][r, :, 0] = 0.0
        data['MCTG'][r, 16, 0] = curt_w[r]
        data['MCTG'][r, 17, 0] = curt_w[r]
        data['MCTG'][r, 18, 0] = curt_s[r]
        
        # %% Load band heights
        # Heights of the load bands
        data['MLB0'][r,3,0] = rldc_prod[3]
        data['MLB0'][r,2,0] = rldc_prod[4]
        data['MLB0'][r,1,0] = rldc_prod[5]
        data['MLB0'][r,0,0] = rldc_prod[6]
        data['MLB0'][r,4,0] = rldc_prod[7]
        if np.sum(Svar*data['MEWS'][r,:,0]) > 0.0:
            CFvar = np.sum(Svar * data['MEWS'][r,:,0] * data['MEWL'][r,:,0]) / np.sum(Svar*data['MEWS'][r,:,0])
        else:
            CFvar = 1.0
            
        # Capacity factors by load band (load bands are defined by these)
        CFLB = np.ones(len(titles['LBTI']))
        CFLB[0] = 7500.0 / 8766.0       # Baseload CF
        CFLB[1] = 4400.0 / 8766.0       # Lower mid-load CF
        CFLB[2] = 2200.0 / 8766.0       # Upper mid-load CF
        CFLB[3] = 700.0 / 8766.0        # Peak load CF
        CFLB[4] = 80.0 / 8766.0         # Backup reserve CF
        CFLB[5] = CFvar               # Intermittent CF
        # Capacity per load band (normalised so that total MGLB == 1, usually total MKLB > 1)
        # Correction: Load-bands relate to load delivered by non-VRE load, i.e. capacity.
        # SUM(MKLB(1:5,J) > 1.0 because of additional backup techs
        # SUM(MKLB(.,J) >> 1.0 because of addition of VRE market shares
        # Rescaling occurs after
        data['MLB1'][r,0,0] = 7500.0 / 8766.0 * max(data['MLB0'][r,0,0], 0.0)
        data['MLB1'][r,1,0] = max(data['MLB0'][r,1,0], 0.0) - max(data['MLB0'][r,0,0], 0.0)
        data['MLB1'][r,2,0] = max(data['MLB0'][r,2,0], 0.0) - max(data['MLB0'][r,1,0], 0.0)
        data['MLB1'][r,3,0] = max(data['MLB0'][r,3,0], 0.0) - max(data['MLB0'][r,2,0], 0.0)
        data['MLB1'][r,4,0] = max(max(data['MLB0'][r,4,0], 0.0) - max(data['MLB0'][r,3,0], 0.0), 0.02)
        # Normalise MKLB[r, :5] by using non-VRE MEWS (they have to sum to the same amount)
        # Given that MEWS adds to 1, so should MKLB do now 
        data['MKLB'][r, :5, 0] = data['MLB1'][r,:5,0] / data['MLB1'][r, :5, 0].sum()
        data['MKLB'][r, :5, 0] = data['MKLB'][r,:5,0] * np.sum(Snotvar*data['MEWS'][r,:,0])
        data['MKLB'][r, 5, 0] = np.sum(Svar * data['MEWS'][r,:,0])
        
        if not np.isclose(data['MKLB'][r, :, 0].sum(), 1.0, atol=10e-6):  # MKLB should sum to ~1
            print(f"Warning: Sum of MKLB for region {r} is not approximately 1. Current sum: {data['MKLB'][r, :, 0].sum()}")
            if np.isnan(data['MKLB'][r, :, 0].sum()):
                nan_indices = np.where(np.isnan(data['MKLB'][r, :, 0]))[0]
                raise ValueError(
                    f"NaN values detected in rldc in data['MKLB'] "
                    f"for region {r} at indices: {nan_indices}.")
        
        # Generation shares
        # Multiply load-bands by their respective LFs
        # MGLB will always be < 1
        # Correct for this by using the average load factor
        # TODO: figure out why this does not sum to 1 (usually 1-5% deviation, sometimes much more)
        # It does not seem MGLB is used elsewhere in the model. 
        data['MGLB'][r,:,0] = data['MKLB'][r,:,0] * CFLB / np.sum(data['MEWS'][r,:,0] * data['MEWL'][r,:,0])
        # if not np.isclose(data['MGLB'][r, :, 0].sum(), 1.0, atol=0.05): # MGLB should sum to ~1
        #     print(f"Warning: Sum of MGLB for region {r} is not approximately 1. Current sum: {data['MGLB'][r, :, 0].sum()}")
        
        
        
        # %%
        #-------------------------------------------------------------
        #-----Long-term storage parameters (Cap, Gen, etc.)-----------
        #-------------------------------------------------------------        
        
        # Residual peak-demand height
        Hp = data['MLB0'][r, 4, 0]
        
        # Non-VRE capacity (or firm capacity)
        cap_notvre = np.sum(Snotvar*data['MEWK'][r, :, 0])
        
        # Hp, peak height, is equal to residual peak load (without LT storage)
        # For LT storage to fill this in, we need MLSC = Hp*(tot_peak_load) - MEWK_non_vre
        cap_needed_0 = Hp * e_dem[r] * 0.175e-3                # 0.175e-3 is a rough estimate to find out peak-load based on demand (MEWD)
        cap_needed_1 = cap_notvre                              # Installed capacity of non-VRE technologies.
        # Smoothing function
        smoothing_fn = 0.5*np.tanh(15*(Hp-1.0))
        # Firm capacity needed (= non-VRE capacity + long-term storage)
        # Apply smoothing here
        cap_needed = (0.5 + smoothing_fn) * cap_needed_1 + (0.5 - smoothing_fn) * cap_needed_0
        data['MLSC'][r, 0, 0] = max(cap_needed - cap_notvre , 0.0) * seasonality_index[r]        
        
        if np.rint(data['MSAL'][r, 0, 0]) == 5:
            # Now estimate the capacity needed due to split responibility
            
            # Wind
            Hp_split_wind = rldc_prod_split_wind[7]
            cap_needed_0_split_wind = Hp_split_wind * e_dem[r] * 0.175e-3  
            smoothing_fn_split_wind = 0.5*np.tanh(15*(Hp_split_wind-1.0))
            cap_needed_split_wind = (0.5 + smoothing_fn_split_wind) * cap_needed_1 + (0.5 - smoothing_fn_split_wind)*cap_needed_0_split_wind
            mlsc_split_wind = max(cap_needed_split_wind - cap_notvre , 0.0) * seasonality_index[r] 
            
            # Solar
            Hp_split_solar = rldc_prod_split_sol[7]
            cap_needed_0_split_solar = Hp_split_solar*e_dem[r] * 0.175e-3  
            smoothing_fn_split_solar = 0.5*np.tanh(15*(Hp_split_solar-1.0))
            cap_needed_split_solar = (0.5 + smoothing_fn_split_solar) * cap_needed_1 + (0.5 - smoothing_fn_split_solar)*cap_needed_0_split_solar
            mlsc_split_solar = max(cap_needed_split_solar - cap_notvre , 0.0) * seasonality_index[r] 
            
        else:
            mlsc_split_wind = 0.0
            mlsc_split_solar = 0.0
            

        # Now that long-term storage capacity has been estimated (effectively as a residual), we calculate
        # how much electricity is delivered to the grid through long-term storage cycles
        # We use fixed parameters and apply them throughout.
        # The marginal effect comes through from marginal changes in storage needs
        # Typically, 100 MW, 70 GWh/cycle. Assume 2 cycles, so 100 MW capacity for every 140 GWh discharched 
        # Or 1400 GWh for 1 GW cap
        total_output_l = data['MLSC'][r, 0, 0] * 1400
        total_input_l = total_output_l/data['MLSE'][r, 0, 0]
        
        # Extra demand due to storage losses (in GWh/y)
        data['MLSG'][r,0,0] = total_input_l - total_output_l
        
        # Effect on electricity price (depends on the MSAL switch whether and how it is allocated)
        # Assume a levelised cost of storage of costs_ls EURO/kWh of electricity discharged
        # Convert the costs to EURO/ GWh of annual demand in order to be added to the electricity price
        # See Figure 2 of https://doi.org/10.1016/j.apenergy.2016.08.165 (H2, 2 cycles)
        # In EURO 2015 / GWh (convert to USD 2013 / GWh in main routine)        
        if np.rint(data['MSAL'][r, 0, 0]) in [1, 2, 3] and np.sum(data['MEWG'][r, :, 0]) > 0.0:
            data['MLSR'][r,0,0] = total_output_l * data['MLCC'][r,0,0] / np.sum(data['MEWG'][r, :, 0])
        elif np.rint(data['MSAL'][r, 0, 0]) in [4, 5] and np.sum(Svar * data['MEWG'][r, :, 0]) > 0.0:
            data['MLSR'][r,0,0] = total_output_l * data['MLCC'][r,0,0] / np.sum(Svar*data['MEWG'][r, :, 0])
            
        # Split responsibilities if MSAL == 5
        if np.rint(data['MSAL'][r, 0, 0]) in [5]:
            
            ratio_ls[r] = 1.0
            # New split for costs
#            if abs(mlsc_split_solar) > 0.0 and abs(data['MLSC'][r,0,0] - mlsc_split_wind) > 0.0:
            ratio_ls[r] = np.sqrt(feqs(mlsc_split_wind) / feqs(mlsc_split_solar) * 
                                   feqs((feqs(data['MLSC'][r,0,0])-feqs(mlsc_split_solar))) /
                                   feqs((feqs(data['MLSC'][r,0,0])-feqs(mlsc_split_wind))) 
                                   )    
        
            LSw = (Sw[r] + Ss[r])/ feqs( (Sw[r] + Ss[r]/ratio_ls[r]) )
            LSs = (Sw[r] + Ss[r])/ feqs( (Sw[r]*ratio_ls[r] + Ss[r]) )           
        
            # Split the average costs over technologies
            data['MLSP'][r, :, 0] = 0.0
            data['MLSP'][r, 16, 0] = data['MLSR'][r,0,0] * LSw
            data['MLSP'][r, 17, 0] = data['MLSR'][r,0,0] * LSw
            data['MLSP'][r, 18, 0] = data['MLSR'][r,0,0] * LSs
        # For option 4, all VRE pay the equal amount
        elif np.rint(data['MSAL'][r, 0, 0]) in [4]:
            data['MLSP'][r, :, 0] = 0.0
            data['MLSP'][r, 16, 0] = data['MLSR'][r,0,0]
            data['MLSP'][r, 17, 0] = data['MLSR'][r,0,0]
            data['MLSP'][r, 18, 0] = data['MLSR'][r,0,0] 
        # All technologies pay the pay amount for the other options
        else:
            data['MLSP'][r,:,0] = data['MLSR'][r,0,0]
            
        #if np.any(data['MLSP'][r,:,0] > 10_000.):
            #print("Long-term storage is pretty high")

        # %%
        #-------------------------------------------------------------
        #-----Short-term storage parameters (Cap, Gen, etc.)----------
        #-------------------------------------------------------------          
        # RLDCProd(2,RLDCregmap(J)) is Short-term Storage capacity in relation to total installed capacity / peak load
        # MSSC(J) is total short-term storage capacity in GW
        # The source for the estimates of capacity needs is: https://doi.org/10.1016/j.eneco.2016.05.012 (SI, 3rd excel file)
        # Short therm storage output delivered back to the grid in relation to total annual demand and inclusive of round-trip efficiency losses
        # 80% round trip efficiency (0.80 is roundtrip efficiency estimate (https://www.pnnl.gov/sites/default/files/media/file/Final%20-%20ESGC%20Cost%20Performance%20Report%2012-11-2020.pdf, average Li-ion, Vanadium)
        # 26.2% is a very rough estimation of the ratio between battery capacity [share peak demand] and storage output [share annual demand]
        # Source comes from https://doi.org/10.1016/j.eneco.2016.05.012 (SI, 3rd excel file)
        total_input = rldc_prod[1] * 0.262 * data['MEWG'][r, :, 0].sum() / data['MSSE'][r, 0, 0]     # Electricity used to charge batteries
        total_output = rldc_prod[1] * 0.262 * data['MEWG'][r, :, 0].sum()                            # Electricity delivered back to the grid
        # Adjust total_output due to seasonality
        total_output = total_output + max(cap_needed - cap_notvre, 0.0) * (1.0-seasonality_index[r]) # Double conversion (capacity/generation ratio different for long + short) 
        data['MSSC'][r,0,0] = rldc_prod[1] * e_dem[r] * 0.175e-3 + max(cap_needed - cap_notvre, 0.0) * (1.0 - seasonality_index[r])
        
        # MSSG =  the additional electricity that needs be generated due to roundtrip efficiency losses
        data['MSSG'][r,0,0] = total_input - total_output
        if data['MSSG'][r,0,0] < 0.0: data['MSSG'][r,0,0] = 0.0
        
        # TODO: In Fortran code, this update does not play a role in the
        # MSSG variable, so that's why this update is after MSSG is calculated
        total_input = total_output / data['MSSE'][r, 0, 0]
        
        
        # Storage cost are overwritten here:
            
        if year >= histend["MSSC_histend"]: 
            
            data['MSSC_histend'] = time_lag['MSSC_histend'].copy()
            data['MLSC_histend'] = time_lag['MLSC_histend'].copy()        
            
            data['MSCC'][:,0,0] = 0.18 * 1e6 * (data_dt['MSSC'][:,0,0].sum() / data['MSSC_histend']) ** learning_exp_ss
            data['MLCC'][:,0,0] = 0.32 * 1e6 * (data_dt['MLSC'][:,0,0].sum() / data['MLSC_histend']) ** learning_exp_ls
            
        # Assumed levelised cost of storage: 0.18 EURO/kWh initially
        # in reality the capacity/energy discharged ratio changes due to demand-supply mismatches.
        # For simplicity a fixed LC is chosen
        # Total costs of electricity discharged to the system per unit of electricity demanded (EURO/GWh):
        # In EURO 2015 / GWh
        if np.rint(data['MSAL'][r, 0, 0]) in [1, 2, 3] and np.sum(data['MEWG'][r, :, 0]) > 0.0:
            data['MSSR'][r,0,0] = total_output * data['MSCC'][r,0,0] / np.sum(data['MEWG'][r, :, 0])
        elif np.rint(data['MSAL'][r, 0, 0]) in [4, 5] and np.sum(Svar * data['MEWG'][r, :, 0]) > 0.0 :
            data['MSSR'][r,0,0] = total_output * data['MSCC'][r,0,0] / np.sum(Svar*data['MEWG'][r, :, 0])
            
        # Split responsibilities for short-term storage (where applicable)
        # NEW: Use ratio ((a/b)*((c-b)/(c-a)))^(1/2)
        if np.rint(data['MSAL'][r, 0, 0]) == 5:
            
            ratio_ss[r] = np.sqrt(feqs(rldc_prod_split_wind[1]) / feqs(rldc_prod_split_sol[1]) *
                                   feqs(feqs(rldc_prod[1]) -feqs(rldc_prod_split_sol[1])) /
                                   feqs(feqs(rldc_prod[1]) - feqs(rldc_prod_split_wind[1])))
            
            # Apply ratios to split the storage costs
            SSw = (Sw[r] + Ss[r]) / feqs( (Sw[r] + Ss[r]/ratio_ss[r]) )
            SSs = (Sw[r] + Ss[r]) / feqs( (Sw[r]*ratio_ss[r] + Ss[r]) )
            
            # Assign price values
            data['MSSP'][r, :,0] = 0.0
            data['MSSP'][r, 16,0] = data['MSSR'][r,0,0] * SSw
            data['MSSP'][r, 17,0] = data['MSSR'][r,0,0] * SSw
            data['MSSP'][r, 18,0] = data['MSSR'][r,0,0] * SSs
        # For option 4, all VRE pay the equal amount
        elif np.rint(data['MSAL'][r, 0, 0]) in [4]:
            data['MSSP'][r,:,0] = 0.0
            data['MSSP'][r,16,0] = data['MSSR'][r,0,0]
            data['MSSP'][r,17,0] = data['MSSR'][r,0,0]
            data['MSSP'][r,18,0] = data['MSSR'][r,0,0] 
        # All technologies pay the pay amount for the other options
        else:
            data['MSSP'][r,:,0] = data['MLSR'][r,0,0]       

        #-------------------------------------------------------------
        #-------------- Marginal costs (where applicable) ------------
        #-------------------------------------------------------------       
        if np.rint(data['MSAL'][r, 0, 0]) in [3, 4, 5]:
            
            #-------------------------------------------------------------
            #---------------- Long-term marginal costs -------------------
            #------------------------------------------------------------- 
            
            # First estimate the costs due to storage (using slightly amplified solar and wind generation shares)
            # Second remove the actual cost of storage.
            # 0.15 is a levelised cost estimate of discharged electricity to the grid (in EURO/kWh)
            # GWh * EURO/kWh * [kWh/GWh] / GWh = EURO / GWh
            # The GWh refer to the annual electricity supplied by wind/solar
            # EURO 2015 / additional GWh
            
            # Total VRE generation
            vre = np.sum(Svar * data['MEWG'][r, :, 0])
            # CSP also taken into account for long-term storage needs
            vre_long = vre + data['MEWG'][r, 19, 0]
            
            # Wind (note we're using a different rldc outcome!)
            Hp_wind = rldc_prod_wind[7]
            cap_needed_0_wind = Hp_wind*e_dem[r]*0.175e-3  
            smoothing_fn_wind = 0.5*np.tanh(15*(Hp_wind-1.0))
            cap_needed_wind = (0.5 + smoothing_fn_wind)*cap_needed_1 + (0.5 - smoothing_fn_wind)*cap_needed_0_wind
            mlsc_wind = max(cap_needed_wind - cap_notvre , 0.0) * seasonality_index[r] 
            
            # Solar
            Hp_solar = rldc_prod_solar[7]
            cap_needed_0_solar = Hp_solar*e_dem[r]*0.175e-3  
            smoothing_fn_solar = 0.5*np.tanh(15*(Hp_solar-1.0))
            cap_needed_solar = (0.5 + smoothing_fn_solar)*cap_needed_1 + (0.5 - smoothing_fn_solar)*cap_needed_0_solar
            mlsc_solar = max(cap_needed_solar - cap_notvre , 0.0) * seasonality_index[r]           
            
            # Typically, 100 MW, 70 GWh/cycle. Assume 2 cycles, so 100 MW capacity for every 140 GWh discharched
            total_output_wind_l = mlsc_wind*1400                  
            total_output_solar_l = mlsc_solar*1400
            total_input_wind_l = total_output_wind_l/data['MLSE'][r, 0, 0]
            total_input_solar_l = total_output_solar_l/data['MLSE'][r, 0, 0]
            
            if np.rint(data['MSAL'][r, 0, 0]) in [3]:
                marg_cost_sol_ls = total_output_solar_l * data['MLCC'][r,0,0] / np.sum(data['MEWG'][r, :, 0] + vre_ggr_sol[r])  - data['MLSP'][r, 18, 0]
                marg_cost_wind_ls = total_output_wind_l * data['MLCC'][r,0,0] / np.sum(data['MEWG'][r, :, 0] + vre_ggr_wind[r])  - data['MLSP'][r, 16, 0]
            elif np.rint(data['MSAL'][r, 0, 0]) in [4]:
                marg_cost_sol_ls = total_output_solar_l * data['MLCC'][r,0,0] / (vre_long + vre_ggr_sol[r]) - data['MLSP'][r, 18, 0]
                marg_cost_wind_ls = total_output_wind_l * data['MLCC'][r,0,0] / (vre_long + vre_ggr_wind[r]) - data['MLSP'][r, 16, 0]
            elif np.rint(data['MSAL'][r, 0, 0]) in [5]:
                marg_cost_sol_ls = total_output_solar_l * data['MLCC'][r,0,0] / (vre_long + vre_ggr_sol[r]) * LSs - data['MLSP'][r, 18, 0]
                marg_cost_wind_ls = total_output_wind_l * data['MLCC'][r,0,0] / (vre_long + vre_ggr_wind[r]) * LSw  - data['MLSP'][r, 16, 0] 
            
            data['MLSM'][r, :, 0] = 0.0
            data['MLSM'][r, 16, 0] = marg_cost_wind_ls
            data['MLSM'][r, 17, 0] = marg_cost_wind_ls
            data['MLSM'][r, 18, 0] = marg_cost_sol_ls            
                
            #-------------------------------------------------------------
            #---------------- Short-term marginal costs ------------------
            #------------------------------------------------------------- 
                        
            # 0.262 is a ratio between storage capacity (in relation to peak demand) and stored electricity discharged (in relation to annual electricity demand) 
            output_sol = rldc_prod_solar[1] * 0.262 * np.sum(data['MEWG'][r, :, 0])
            output_sol = output_sol + max(cap_needed_solar - cap_notvre, 0.0) * (1.0 - seasonality_index[r]) / 0.175e-3 * 0.262    # Add extra output from peak load sufficiency
            #output_sol = output_sol + total_output_solar_l # add short-term storage from capacity needs
            input_sol = output_sol / data['MSSE'][r, 0, 0]  

            output_wind = rldc_prod_wind[1] * 0.262 * np.sum(data['MEWG'][r, :, 0])
            output_wind = output_wind + max(cap_needed_wind - cap_notvre, 0.0) * (1.0 - seasonality_index[r]) / 0.175e-3 * 0.262   # Add extra output from peak load sufficiency
            # output_wind = output_wind + total_output_wind_l # add short-term storage from capacity  needs
            input_wind = output_wind / data['MSSE'][r, 0, 0]            
            
            if np.rint(data['MSAL'][r, 0, 0]) in [3]:
                marg_cost_sol_ss = output_sol * data['MSCC'][r,0,0] / np.sum(data['MEWG'][r, :, 0] + vre_ggr_sol[r])  - data['MSSP'][r, 18, 0]
                marg_cost_wind_ss = output_wind * data['MSCC'][r,0,0] / np.sum(data['MEWG'][r, :, 0] + vre_ggr_wind[r])  - data['MSSP'][r, 16, 0]
            elif np.rint(data['MSAL'][r, 0, 0]) in [4]:
                marg_cost_sol_ss = output_sol * data['MSCC'][r,0,0] / (vre + vre_ggr_sol[r]) - data['MSSP'][r, 18, 0]
                marg_cost_wind_ss = output_wind * data['MSCC'][r,0,0] / (vre + vre_ggr_wind[r]) - data['MSSP'][r, 16, 0]
            elif np.rint(data['MSAL'][r, 0, 0]) in [5]:
                marg_cost_sol_ss = output_sol * data['MSCC'][r,0,0] / (vre + vre_ggr_sol[r]) * SSs - data['MSSP'][r, 18, 0] 
                marg_cost_wind_ss = output_wind * data['MSCC'][r,0,0] / (vre + vre_ggr_wind[r]) * SSw  - data['MSSP'][r, 16, 0] 

                    
            data['MSSM'][r,:,0] = 0.0
            data['MSSM'][r,16,0] = marg_cost_wind_ss
            data['MSSM'][r,17,0] = marg_cost_wind_ss
            data['MSSM'][r,18,0] = marg_cost_sol_ss 
            
  

    # Store the storage capacities in last historical year
    if year <= histend["MSSC_histend"]:
        data['MSSC_histend'] = np.sum(data['MSSC']).copy()
        data['MLSC_histend']  = np.sum(data['MLSC']).copy()         


    return data
