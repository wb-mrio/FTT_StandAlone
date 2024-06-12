# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 11:54:30 2024

@author: WRI India, Femke, Cormac

=========================================
ftt_h_steel.py
=========================================
Steel production module.
####################################

This is the main file for FTT: Steel, which models technological
diffusion of residential heating technologies due to simulated consumer decision making.
Consumers compare the **levelised cost of heat**, which leads to changes in the
market shares of different technologies.

The outputs of this module include changes in final energy demand and boiler sales.

Local library imports:

    Support functions:

    - `divide <divide.html>`__
        Bespoke element-wise divide which replaces divide-by-zeros with zeros
    - `estimation <econometrics_functions.html>`__
        Predict future values according to the estimated coefficients.

Functions included:
    - solve
        Main solution function for the module
    - get_lcoh
        Calculate levelised cost of residential heating

"""
# Standard library imports
from math import sqrt
import copy
import warnings

# Third party imports
import numpy as np

# Local library imports
from SourceCode.support.divide import divide
from SourceCode.ftt_core.ftt_s_sales_or_investments import get_sales
from SourceCode.Steel.ftt_s_lcos import get_lcos
from SourceCode.Steel.ftt_s_scrap import scrap_calc
from SourceCode.Steel.ftt_s_rawmaterials import raw_material_distr
from SourceCode.Steel.ftt_s_fuel_consumption import ftt_s_fuel_consumption

# -----------------------------------------------------------------------------
# ----------------------------- Main ------------------------------------------
# -----------------------------------------------------------------------------
def solve(data, time_lag, iter_lag, titles, histend, year, specs):
    """
    Main solution function for the module.

    Add an extended description in the future.

    Parameters
    -----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution
    time_lag: type
        Description
    iter_lag: type
        Description
    titles: dictionary of lists
        Dictionary containing all title classification
    histend: dict of integers
        Final year of histrorical data by variable
    year: int
        Curernt/active year of solution
    specs: dictionary of NumPy arrays
        Function specifications for each region and module

    Returns
    ----------
    data: dictionary of NumPy arrays
        Model variables for the given year of solution

    Notes
    ---------
    This function should be broken up into more elements in development.
    """

    # Categories for the cost matrix (BSTC)
    c5ti = {category: index for index, category in enumerate(titles['C5TI'])}
    # Fuels
    jti = {category: index for index, category in enumerate(titles['JTI'])}

    sector = 'steel'
    no_it = data["noit"][0, 0, 0]

    data = scrap_calc(data, time_lag, titles, year)

    # Historical data currently ends in 2019, so we need to initialise data
    # Simulation period starts in 2020   # Calculate capacities (SEWK)
    if year <= histend['SEWG']:

        # Connect historical data to future projections (only for DATE == 2014)
        
        for r in range(len(titles['RTI'])):
            # data['SEWG'] is in historic sheets, so no need to calculate that.
        
            # Capacity (kton) (11th are capacity factors) 
            data['SEWK'][r, :, 0] = 0.0
            data['SEWK'][r, :, 0] = data['SEWG'][r, :, 0] / data['BSTC'][r, :, c5ti["CF"]]
            data['SPSA'][r, 0, 0] = sum(data['SEWG'][r, :, 0])
        
            # 'Historical' employment in th FTE 
            data['SEMS'][r, :, 0] = data['SEWK'][r, :, 0] * data['BSTC'][r, :, c5ti["Employment"]] * 1.1
        
            # In this preliminary model SPSP is historical production while SPSA is exogenous future production (based on E3ME baseline)
            # Total steel production by region (kton/y) = demand
            # SPSP[j] = sum(data['SEWG'][:, j])
            
            # Market capacity shares of steelmaking technologies: 
            data['SEWS'][r, :, 0] = 0
            data['SEWS'] [r, :, 0] = np.divide (data['SEWK'][r, :, 0], np.sum(data['SEWK'][r, :, 0]),
                                                where =(data['SPSP'][r, 0, 0] > 0.0) and (data['SEWK'][r, :, 0] > 0.0)) 
                
            # Emissions (MtCO2/y) (13th is emissions factors tCO2/tcs)
            # A crude backwards calculation of emissions using simple emission factors keep
            data['SEWE'][r, :, 0] = data['SEWG'][r, :, 0] * data['BSTC'][r, :, c5ti["EF"]] / 1000
        
            # Regional average energy intensity (GJ/tcs) 
            data['STEI'][r, :, 0] = data['BSTC'][r, :, c5ti["Energy Intensity"]]
            data['SEIA'][r, 0, 0] = sum(data['STEI'][r, :, 0] * data['SEWS'][r, :, 0])

        if year == 2019:
            data['SPSA'] = data['SPSP']
            raw_material_distr(data, titles, year, 1)
        
            # Calculate fuel use (SJEF)
            #Set
            sewg_sum = np.sum(data["SEWG"], axis=1)
            og_base = np.zeros_like(sewg_sum)

            og_base[sewg_sum > 0.0] = np.sum(data["SEWG"][:, 0:7], axis=1)[sewg_sum > 0.0] / sewg_sum[sewg_sum > 0.0]
            og_sim = og_base
            #ccs_share = 0.0

            ftt_s_fuel_consumption(data['BSTC'], data['SEWG'], data['SMED'], len(titles['RTI']), len(titles['STTI']), c5ti, len(titles['JTI']))
        
            # for r in range(len(titles['RTI'])):
            #     for i in range(len(titles['STTI'])):
            #     # Calculate fuel consumption
                
            #         data['SJEF'][r,0,0] += data['BSTC'][r, i,c5ti["Hard Coal"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,11,0] * 1/41868
            #         data['SJEF'][r,1,0] += data['BSTC'][r,i,c5ti["Other Coal"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,12,0] * 1/41868
            #         data['SJEF'][r,6,0] += data['BSTC'][r,i,c5ti["Natural Gas"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,13,0] * 1/41868
            #         data['SJEF'][r,7,0] += data['BSTC'][r,i,c5ti["Electricity"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,14,0] * 1/41868
            #         data['SJEF'][r,10,0] += ((data['BSTC'][r,i,c5ti["Biocharcoal"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,18,0] * 1/41868) + (data['BSTC'][r,i,c5ti["Biogas"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,19,0] * 1/41868))
            #         data['SJEF'][r,11,0] += data['BSTC'][r,i,c5ti["Hydrogen"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,17,0] * 1/41868
                    
            #         if (data['BSTC'][r,i,21] == 1):
            #             data['SJCO'][r,0,0] += 0.1 * data['BSTC'][r,i,c5ti["Hard Coal"]]*data['SEWG'][r,i,0]* 1000 * data['SMED'][0,11,0]*1/41868
            #             data['SJCO'][r,1,0] += 0.1 * data['BSTC'][r,i,c5ti["Other Coal"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,12,0] * 1/41868
            #             data['SJCO'][r,6,0] += 0.1 * data['BSTC'][r,i,c5ti["Natural Gas"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,13,0] * 1/41868
            #             data['SJCO'][r,7,0] += data['BSTC'][r,i,c5ti["Electricity"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,14,0] * 1/41868
            #             data['SJCO'][r,10,0] += -0.9 * ((data['BSTC'][r,i,c5ti["Biocharcoal"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,14,0] * 1/41868) + (data['BSTC'][r,i,c5ti["Biogas"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,19,0] * 1/41868))
            #             data['SJCO'][r,11,0] += data['BSTC'][r,i,c5ti["Hydrogen"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,17,0] * 1/41868
                    
            #         else:
            #             data['SJCO'][r,0,0] += data['BSTC'][r,i,c5ti["Hard Coal"]]*data['SEWG'][r,i,0]* 1000 * data['SMED'][0,11,0]*1/41868
            #             data['SJCO'][r,1,0] += data['BSTC'][r,i,c5ti["Other Coal"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,12,0] * 1/41868
            #             data['SJCO'][r,6,0] += data['BSTC'][r,i,c5ti["Natural Gas"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,13,0] * 1/41868
            #             data['SJCO'][r,7,0] += data['BSTC'][r,i,c5ti["Electricity"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,14,0] * 1/41868
            #             data['SJCO'][r,10,0] += 0.0
            #             data['SJCO'][r,11,0] += data['BSTC'][r,i,c5ti["Hydrogen"]] * data['SEWG'][r, i, 0]* 1000 * data['SMED'][0,17,0] * 1/41868
            
            data['SJFR'] = data['SJEF']
           
            #Call the LCOS function within the year==2019 conditional statement
            data = get_lcos(data, titles)
                
            # Calculate cumulative capacities (SEWW)

            
            bi = np.zeros((len(titles['RTI']), len(titles['STTI'])))

            for r in range(len(titles['RTI'])):
                bi[r,:] = np.matmul(data['SEWB'][0, :, :], data['SEWK'][r, :, 0])
                data['SEWW'] = np.sum (bi, axis = 0)
            
            data['SEWW'] = data['SEWW'][None, :, None]

            #This needs to be in the year==2019 conditional statement
            #These 2 loops happen twice. Let's just make it a separate function and call it here and in year > histend
            for t1 in range(len(titles['STTI'])): 
                for t2 in range(len(titles['SSTI'])):
                    if data['STIM'][0, t1, t2] == 1:
                        if (t2 < 8): 
                            data['SICA'][:, t2, 0] = data['SICA'][:, t2, 0] + 1.1 * data['SEWW'][0, t1, 0] * np.sum(data['BSTC'][:, t1, 25+t2])/np.count_nonzero(data['SPSA'][:, :, 0])
                    
                        elif (t2 > 7 and t2 < 21):
                                data['SICA'][:, t2, 0] = data['SICA'][:, t2, 0] + 1.1 * data['SEWW'][: , t1 , 0] 
                        # Estimate installed capacities of steelmaking plants
                        elif (t2 > 20 and t2 < 27): 
                            data['SICA'][:, t2, 0] = data['SICA'][:, t2, 0] + data['SEWW'][:, t1, 0] 
                        # Estimate installed capacities of finishing plants. 
                        # Note that after this step it's not crude steel anymore. Therefore it is divided by 1.14  
                        elif (t2 == 27):
                            data['SICA'][:, t2, 0] = data['SICA'][:, t2, 0] + data['SEWW'][:, t1, 0] /1.14 
            
            
            data['SEWI'][: , : , 0] = np.where((data['BSTC'][: , : , 5] > 0.0) , (data['SEWI'][: , : , 0] + (data['SWKL'][: , :, 0]/data['BSTC'][: , : , 5])) , np.max((data['SEWK'][: , : , 0] - data['SWKL'][: , : , 0]), 0))
        
                                             
        if year > histend["SEWG"]:
            no_it = int(data['noit'][0, 0, 0])
            dt = 1 / float(no_it)
            invdt = no_it
            tScaling = 10.0
            isReg = np.zeros((len(titles['RTI']), len(titles['STTI'])))
            for t in range(1, no_it):
                
                # Create a local dictionary for timeloop variables
                # It contains values between timeloop interations in the FTT core
                data_dt = {}

                # First, fill the time loop variables with the their lagged equivalents
                for var in time_lag.keys():
                    data_dt[var] = copy.deepcopy(time_lag[var])
                raw_material_distr(data, titles, year, t)
                # Market share calculation : What Shruti has done
                       
            
            # --------------------------------------------------------------------------
            # !--------------FTT SIMULATION-----------------------------------------------
            # !---------------------------------------------------------------------------
            # !------TIME LOOP!!: we calculate quarterly: t=1 means the end of the first quarter            
                 
            if (iter==1):  
                    for t in range(0, (invdt - 1)):
                        data_dt['SPSA'][0, 0, 0] = 0.0
                                        
                # Time-step of steel demand
            data_dt['SPSA'][:, 0, 0] = data['SPSL'][:, 0, 0] + data['SPSA'][:, 0, 0] - data['SPSL'][:, 0, 0] * t/invdt
            data_dt['SPSA'][:, 0, 0] = data['SPSL'][:, 0, 0] + data['SPSA'][:, 0, 0] - data['SPSL'][:, 0, 0] * (t-1)/invdt
                            
            primary_iron_supply = 0.0
            primary_iron_demand = 0.0
            #primary_iron_supply = SUM( SWGI(:,J) * (0.9 - BSTC(:,J,12)) )
            #primary_iron_demand = (1-BSTC(26,J,25)/1.1) * SWKL(26,J) * BSTC(26,J,12)
            
            #If there's not enough scrap to supply the scrap route or there's not enough iron supply to meet the gap of scrap supply, then regulate scrap. 
            #This is more of a weak regulation. 
                        
            # Calculate the condition for the first WHERE statement
            condition1 = (~(data['SEWR'][:, 25, 0] > data_dt['SWKL'][:, 25, 0])) & (data['SEWR'][:, 25, 0] > -1.0)

            # Apply the first WHERE statement
            isReg[:, 25] = np.where(condition1, 1.0 - np.tanh(2 * 1.25 * data_dt['BSTC'][:, c5ti['Scrap'], c5ti['Scrap']] - 0.5) / 0.5, isReg[:, 25])

            # Calculate the condition for the second WHERE statement
            condition2 = (isReg[:, 25] > 1.0)

            # Apply the second WHERE statement
            isReg[:, 25] = np.where(condition2, 1.0, isReg[:, 25])
                               
                            
            condition = (~(data['SEWR'][:, 25, 0] > data_dt['SWKL'][:, 25, 0])) & (data['SEWR'][:, 25, 0] > -1.0)
            isReg[25, :] = np.where(condition, 1.0 - np.tanh(((2 * 1.25 * data_dt['BSTC'][:, 25, 25] - 0.5) / 0.5)))        
            isReg[25, :] = np.where(isReg[25,:] > 1.0, 1.0)
                                
                            
############################ FTT ##################################
#                        t3 = time.time()
#                        print("Solving {}".format(titles["RTI"][r]))
# Initialise variables related to market share dynamics
# DSij contains the change in shares           
            for r in range(len(titles['RTI'])):    
                dSij = np.zeros([len(titles['STTI']), len(titles['STTI'])])   
                F = np.ones([len(titles['STTI']), len(titles['STTI'])]) * 0.5
                FE = np.ones([len(titles['STTI']), len(titles['STTI'])]) * 0.5
                            
                for b1 in range(len(titles['STTI'])): 
                       if  not (data['SEWS'][r, b1, 0] > 0.0 and
                                data['SGC1'][r, b1, 0] != 0.0 and
                                data['SEWC'][r, b1, 0] != 0.0):
                                continue
                            
                       S_i = data['SEWS'][r, b1, 0]
                            
                       for b2 in range(b1):                 
                              if not (data['SEWS'][r, b2, 0] > 0.0 and
                                      data['SGC1'][r, b2, 0] != 0.0 and 
                                      data['SEWC'][r, b2, 0] != 0.0): 
                                  continue                      
                               
                              S_k = data['SEWS'][r, b2, 0]
                            
                # Propagating width of variations in perceived costs
                dFij = 1.414 * sqrt((data_dt['SEWC'][r, b1, 0] * data_dt['SEWC'][r, b1, 0] 
                                     + data_dt['SEWC'][r, b2, 0] * data_dt['SEWC'][r, b2, 0]))
                        
                # Consumer preference incl. uncertainty
                Fij = 0.5 * (1 + np.tanh(1.25 * (data_dt['SGC1'][r, b2, 0]
                             - data_dt['SGC1'][r, b1, 0])) / dFij)
                        
                 # Preferences are then adjusted for regulations
                F[b1, b2] = Fij * (1.0 - isReg[r, b1]) * (1.0 - isReg) + isReg[r, b2] \
                                            * (1.0 - isReg[r, b1]) + 0.5 * (isReg[r, b1] * isReg[r, b2])
                F[b2, b1] = (1.0 - Fij) * (1.0 - isReg[r, b2]) * (1.0 - isReg[r, b1]) + isReg[r, b1] \
                                            * (1.0 - isReg[r, b2]) + 0.5 * (isReg[r, b2] * isReg[r, b1])
                        
                #Runge-Kutta market share dynamiccs
                k_1 = S_i * S_k * (data['SEWA'][0, b1, b2] * F[b1,b2] - data['SEWA'][0, b2, b1]* F[b2,b1])
                k_2 = (S_i + dt * k_1/2) * (S_k - dt * k_1/2) * (data['SEWA'][0, b1, b2] * F[b1,b2] - data['SEWA'][0, b2, b1] * F[b2,b1])
                k_3 = (S_i + dt * k_2/2) * (S_k - dt * k_2/2) * (data['SEWA'][0, b1, b2] * F[b1,b2]- data['SEWA'][0, b2, b1]  * F[b2,b1])
                k_4 = (S_i + dt * k_3) * (S_k - dt * k_3) * (data['SEWA'][0, b1, b2] * F[b1,b2] - data['SEWA'][0, b2, b1] * F[b2,b1])
                        
                dSij[b1, b2] = dt * (k_1+2*k_2+2*k_3+k_4)/6/tScaling
                dSij[b2, b1] = -dSij[b1, b2]
                
                # -----------------------------------------------------
                # Step 2: Endogenous premature replacements
                # -----------------------------------------------------
                # Initialise variables related to market share dynamics
                #  DSiK contains the change in shares
                # !This is due to more plants being eligible for scrapping. However, the investor preference should be much lower than the one from above.
                SR = np.zeros(len(titles['RTI']))
                SR = 1/data['BSTC'][r, :, c5ti['Payback period']] - 1/data['BSTC'][r, :, c5ti['Lifetime']]
                    
                # Constant used to reduce the magnitude of premature scrapping 
                SR_C = 2.5
                #!Only calculate for non-zero shares (SWSLt>0), only if scrapping decision rate > 0
                dSEij = np.zeros([len(titles['STTI']), len(titles['STTI'])])
        
                # F contains the preferences
                FE = np.ones([len(titles['STTI']), len(titles['STTI'])])*0.5
                                  
                for b1 in range(len(titles['STTI'])):       
                       if not (data_dt['SEWS'][r, b1, 0] > 0.0 and
                               data_dt['SGC2'][r, b1, 0] != 0.0 and
                               data_dt['SGD2'][r, b1, 0] != 0.0 and
                               data_dt['SGC3'][r, b1, 0] != 0.0 and
                               data_dt['SGD3'][r, b1, 0] != 0.0 and
                               SR[b1] > 0.0):
                           continue
    
                       SE_i = data_dt['SEWS'][r, b1, 0]
            
                       for b2 in range(b1):       
                              if not (data_dt['SEWS'][r, b2, 0] > 0.0 and
                                      data_dt['SGC2'][r, b2, 0] != 0.0 and
                                      data_dt['SGD2'][r, b2, 0] != 0.0 and
                                      data_dt['SGC3'][r, b2, 0] != 0.0 and
                                      data_dt['SGD3'][r, b2, 0] != 0.0 and
                                      SR[b2] > 0.0):
                                  continue
        
                              SE_k = data_dt['SEWS'][r, b2, 0]
        
                            
                        
            # Only calculate for non-zero shares (SWSLt>0), only if scrapping decision rate > 0
            if data['SWSL'][r, b1, 0] > 0:
                          dSEij = 0
            # Propagating width of variations in perceived costs
            dFEij = 1.414 * sqrt((data_dt['SGD3'][r, b1, 0] * data_dt['SGD3'][r, b1, 0] + data_dt['SGD2'][r, b2, 0] * data_dt['SGD2'][r, b2, 0]))
            dFEji = 1.414 * sqrt((data_dt['SGD2'][r, b1, 0] * data_dt['SGD3'][r, b1, 0] + data_dt['SGD3'][r, b2, 0] * data_dt['SGD3'][r, b2, 0]))
                
            # Preferences based on cost differences by technology pairs (asymmetric!)
            FEij = 0.5*(1+np.tanh(1.25*(data_dt['SGC2'][r, b2, 0] - data_dt['SGC3'][r, b1, 0])/dFEij))
            FEji = 0.5*(1+np.tanh(1.25*(data_dt['SGC2'][r, b1, 0] - data_dt['SGC3'][r, b2, 0])/dFEji))
    
            # Preferences are either from investor choices (FEij) or enforced by regulations (HREG)
            FE[b1, b2] = FEij*(1.0-isReg[r, b1])
            FE[b2, b1] = FEji*(1.0-isReg[r, b2])
                                
            # -------Shares equation!! Core of the model!!------------------ 
            # dSEij(I,K) = SWSLt(I,J)*SWSLt(K,J)*(SWAP(I,K)*FE(I,K)*SR(K,J)/SR_C - SWAP(K,I)*FE(K,I)*SR(I,J)/SR_C)*dt
            # ------Runge-Kutta Algorithm (RK4) implemented by RH 5/10/22, do not remove the divide-by-6!--------!
            kE_1 = SE_i * SE_k * (data['SWAP'][0, b1, b2] * FE[b1,b2] * SR[b2]/SR_C - data['SWAP'][0, b2, b1] * FE[b2, b1] * SR[b1]/SR_C)
            kE_2 = (SE_i + dt * kE_1/2) * (SE_k - dt * kE_1/2) * (data['SWAP'][0, b1, b2] * FE[b1,b2] * SR[b2]/SR_C - data['SWAP'][0, b2, b1] * FE[b2,b1]*SR[b1]/SR_C)
            kE_3 = (SE_i + dt * kE_2/2) * (SE_k - dt * kE_2/2) * (data['SWAP'][0, b1, b2] * FE[b1,b2] * SR[b2]/SR_C - data['SWAP'][0, b2, b1] * FE[b2,b1]*SR[b1]/SR_C)
            kE_4 = (SE_i + dt * kE_3) * (SE_k - dt * kE_3) * (data['SWAP'][0, b1, b2] * FE[b1,b2] * SR[b2]/SR_C - data['SWAP'][0, b2, b1] * FE[b2,b1]*SR[b1]/SR_C)
                                      
            dSEij[b1, b2] = dt * (kE_1+2*kE_2+2*kE_3+kE_4)/6/tScaling
            dSEij[b2, b1] = -dSEij[b1, b2]
                                          
            #  !------End of RK4 Alogrithm!------------------------------------------------------------------------!                                             
            # Calulate endogenous shares!
                
            endo_shares = data_dt['SWSL'][r, :, 0] + np.sum(dSij, axis=1) + np.sum(dSEij, axis=1)
            endo_eol =  np.sum(dSij, axis=1) 
            endo_capacity = data_dt['SPSA'][r, :, 0]/np.sum(endo_shares * data['BSTC'][r, :, c5ti['CF']]) * endo_shares
            # Note: for steel, shares are shares of generation
            endo_gen = endo_capacity * data['BSTC'][r, :, c5ti['CF']]                                       
            demand_weight = np.sum(endo_shares * (data['BSTC'][r, :, c5ti['CF']]))
                                
                                                
            Utot = np.sum(endo_shares * demand_weight)
            dUk = np.zeros([len(titles['STTI'])])
            dUkSK = np.zeros([len(titles['STTI'])])
            dUkREG = np.zeros([len(titles['STTI'])])
            #dUkKST = np.zeros([len(titles['STTI'])])
                                        
                            
            # Kickstart in terms of SPSAt
            dUkKST = np.where(data['SWKA'][r, :, 0] < 0,
                              data['SKST'][r, :, 0] * Utot * dt, 0)
                                       
            # Regulations have priority over kickstarts
            dUkKST = np.where(((dUkKST / data['BSTC'][r, :, c5ti['CF']]) + endo_capacity > data['SEWR'][r, :, 0]) & (data['SEWR'][r, :, 0] >= 0.0),
                              0,
                              dUkKST)
            # Shares are shares of demand, divided by average capacity factor 
            # Regulation is done in terms of shares of raw demand (no weighting)
            # Correct for regulations using difference between endogenous demand and demand from last time step with endo shares
            dUkREG = np.where((endo_capacity * demand_weight - (endo_shares * data['SPSA'][r, 0, 0])) > 0, 
                              - ((endo_capacity * demand_weight) - endo_shares * data['SPSA'][r, 0, 0]) * isReg[r, :],
                              0)                                                
            # Calculate demand subtractions based on exogenous capacity after regulations and kickstart, to prevent subtractions being too large and causing negatve shares.
            # Convert to direct shares of SPSAt - no weighting!
            dUkSK = np.where((data['SWKA'][r, :, 0] > endo_capacity) & (data['SWKA'][r, :, 0] > data ['SWKL'][r, :, 0]),
                              ((data['SWKA'][r, :, 0] - endo_capacity) * demand_weight - dUkREG - dUkKST) * (t/invdt),
                              0)                                    
            # If SWKA is a target and is larger than the previous year's capacity, treat as a kick-start based on previous year's capacity. Small additions will help the target be met. 
            dUkSK = np.where((data['SWKA'][r, :, 0] > endo_capacity) & (data['SWKA'][r, :, 0] > data ['SWKL'][r, :, 0]),
                            (data['SWKA'][r, :, 0] - endo_capacity) * demand_weight * (t/invdt),
                             dUkSK)                                                                        
            # Regulations have priority over exogenous capacity
            dUkSK = np.where((data['SWKA'][r, :, 0] < 0) | (data['SEWR'][r, :, 0] >= 0) & (data['SWKA'][r, :, 0] > data['SEWR'][r, :, 0]),
                            0, dUkSK)
        
                                                               
            dUk = dUkREG + dUkSK + dUkKST
            dUtot  = np.sum(dUk)
                                        
                                            
            #Use modified shares of demand and total modified demand to recalulate market shares
            #This method will mean any capacities set to zero will result in zero shares
            #It avoids negative shares
            #All other capacities will be stretched, depending on the magnitude of dUtot and how much of a change this makes to total capacity/demand
            #If dUtot is small and implemented in a way which will not under or over estimate capacity greatly, SWKA is fairly accurate
        
            #Market share changes due to exogenous settings and regulations
            if np.sum((endo_capacity * demand_weight) + dUk) > 0:
                data['SWSA'][r, :, 0] = dUk/np.sum((endo_capacity * demand_weight) + dUk)
                           
            #New market shares
            if np.sum((endo_capacity * demand_weight) + dUk) > 0:
                data['SEWS'][r, :, 0] = (((endo_capacity * demand_weight) + dUk)/np.sum(endo_capacity * demand_weight) + dUk)
                                      
            #Changes due to end-of-lifetime replacements
            data['SEOL'][r, :, 0] = np.sum(dSij, axis = 1)
            #Changes due to premature scrapping
            data['SBEL'][r, :, 0] = np.sum(dSEij,axis = 1)
            
            #--Main variables once we have new shares:--
            #Steel production capacity per technology (kton)
            data['SEWK'][r, :, 0] = (data['SPSA'][r, :, 0])/np.sum(data['SEWS'][r, :, 0] * data['BSTC'][r, :, c5ti['CF']] * data['SEWS'][r, :, 0])
            #Actual steel production per technology (kton) (capacity factors column 12)
            data['SEWG'][r, :, 0] = (data['SEWK'][r, :, 0] * data['BSTC'][r, :, c5ti['CF']])
            #Emissions (MtCO2/y) (14th is emissions factors tCO2/tcs)
            #data['SEWE'][r, :, 0] = (data['SEWG'][r, :, 0] * data ['STEF'][r, :, 0])/1e3
            
                            
                   
            #EOL replacements based on shares growth
            eol_replacements_t = np.zeros([len(titles['RTI'])])
            eol_replacements = np.zeros([len(titles['RTI'])])
            
            if (iter==1):  
                for t in range(0, (invdt - 1)):
                    data['SEWI'][r, :, 0] = 0.0
                    data_dt['SEWI'][r, :, 0] = 0.0
            
                                                 
            eol_replacements_t = np.where((endo_eol >= 0 & (data['BSTC'][r, :, c5ti['Lifetime']] > 0), 
                                           (data['SWKL'][r, :, 0] * dt/data['BSTC'][r, :, c5ti['Lifetime']])), 0)
            
            eol_replacements_t = np.where(((data['SWSL'][r, :, 0]) * dt/data['BSTC'][r, :, c5ti['Lifetime']] < endo_eol < 0) & data['BSTC'][r, :, c5ti['Lifetime']] > 0, 
                                           (data['SEWS'][r, :, 0] - data['SWSL'][r, :, 0] + data['SWSL'][r, :, 0] * dt/data['BSTC'][r, :, c5ti['Lifetime']]) * data['SWKL'][r, :, 0], eol_replacements_t) 
            
            # Capacity growth
            if (data['SEWK'][r, :, 0] - data['SWKL'][r, :, 0]) > 0 :
                 data['SEWI'][r, :, 0] = data['SEWK'][r, :, 0] - data['SWKL'][r, :, 0] + eol_replacements_t
            else:
                 data['SEWI'][r, :, 0] = eol_replacements_t
            
            # Capacity growth, add each time step to get total at end of loop
            data['SEWI'][r, :, 0] = data['SEWI'][r, :, 0] + data['SEWI'][r, :, 0]             
                        
            # Check what investment and learning thing comes here from line 800 to 844 in Fortran
            # Cumulative investment for learning cost reductions
            # (Learning knowledge is global Therefore we sum over regions)
            # BI = MATMUL(SEWB,SEWIt)          Investment spillover: spillover matrix B
            # dW = SUM(BI,dim=2)         Total new investment dW (see after eq 3 Mercure EP48)

            sewi0= np.sum(sewi_t, axis=1)
            for path in range(len(titles['STTI'])):
                dw_temp = sewi0
                dw[path] = np.matmul(dw_temp, data['SEWB'][:, path, :])
            
            #Cumulative capacity for learning
            data['SEWW'] = data_dt['SWWL'] + dw

            #Update technology costs for both the carbon price and for learning
            #Some costs do not change

            data['BSTC'][: , : , 0:21] = data_dt['BSTL'][: , : , 0:21]
            data['SCMM']= data_dt['SCML']

            # for j in range(len(titles['RTI'])):
            #     #Switch: Do governments feedback xx% of their carbon tax revenue as energy efficiency investments?
            #     #Government income due to carbon tax in mln$(2008) 13/3/23 RSH: is this 2008 or 2013 as the conversion suggests?
            # Lines 820 to 844 relate to E3ME variables
            # New additions (SEWI)
            data, sewi_t = get_sales(data['SEWK'], data_dt['SEWK'], time_lag['SEWK'], data['SEWS'], data_dt['SEWS'], data['SEWI'], data['BSTC'][:, :, c5ti['Lifetime']], dt)
            ############## Learning-by-doing ##################

            # Cumulative global learning
            # Using a technological spill-over matrix (HEWB) together with capacity
            # additions (SEWI) we can estimate total global spillover of similar
            # technologies
            bi = np.zeros((len(titles['RTI']),len(titles['STTI'])))
            for r in range(len(titles['RTI'])):
                 bi[r,:] = np.matmul(data['SEWB'][0, :, :],sewi_t[r, :, 0])
            dw = np.sum(bi, axis=0)

            # Cumulative capacity incl. learning spill-over effects
            data['SEWW'][0, :, 0] = data_dt['SEWW'][0, :, 0] + dw

            # Copy over the technology cost categories that do not change (all except prices which are updated through learning-by-doing below)
            data['BSTC'] = copy.deepcopy(data_dt['BSTC'])

            # Learning-by-doing effects on investment and efficiency
            for b in range(len(titles['STTI'])):

                if data['SEWW'][0, b, 0] > 0.0001:

                    data['BSTC'][:, b, c5ti['1 Inv cost mean (EUR/Kw)']] = (data_dt['BSTC'][:, b, c5ti['1 Inv cost mean (EUR/Kw)']]  \
                                                                              *(1.0 + data['BSTC'][:, b, c5ti['7 Investment LR']] * dw[b]/data['SEWW'][0, b, 0]))
                    data['BSTC'][:, b, c5ti['2 Inv Cost SD']] = (data_dt['BHTC'][:, b, c5ti['2 Inv Cost SD']]  \
                                                                              *(1.0 + data['BSTC'][:, b, c5ti['7 Investment LR']] * dw[b]/data['SEWW'][0, b, 0]))

            #Total investment in new capacity in a year (m 2014 euros):
              #SEWI is the continuous time amount of new capacity built per unit time dI/dt (GW/y)
              #BHTC(:,:,1) are the investment costs (2014Euro/kW)
            data['SWIY'][:,:,0] = data['SWIY'][:,:,0] + data['SEWI'][:,:,0]*dt*data['BSTC'][:,:,0]/data['PRSC14'][:,0,0,np.newaxis]
            # Save investment cost for front end
            data["SWIC"][:, :, 0] = data["BSTC"][:, :, c5ti['1 Inv cost mean (EUR/Kw)']]
            
            # Add lines 884 to 905 from Fortran (LBD)
            sica_lr = -0.015
            #Calculate learning in terms of energy/material consumption
            for mat in range(len(titles['SMTI'])):
                 for plant in range(len(titles['SSTI'])):
                      if(data['SICA'][0, plant, 0] > 0.0):
                           data['SCMM'][0, mat, plant] = (data_dt['SCML'][0, mat, plant] - data['SEEM'][0, mat, plant]) * (1.0 + (sica_lr[0,plant]) * ((data['SICA'][0, plant, 0]-data_dt['SICL'][0, plant, 0])/data_dt['SICL'][0, plant, 0])) + data['SEEM'][0, mat, plant]

            #Update material and cost input output matrix
            data['SLCI'][:, 4, 10] = data['SCMM'][:, 0, 6]

            #Redistribute materials
            if (iter < 10 and t == invdt):
                raw_material_distr(data, titles, year, t)

            #Regional average energy intensity (G/tcs)
            data['SEIA'] = np.sum((data['STEI'] * data['SEWS']), axis = 0)

            #Calculate bottom-up employment growth rates
            data['SEMS'] = data['SEWK'] * data['BSTC'][ :, : , 4] * 1.1
            data['SEMR'] = np.where((np.sum(data_dt['SMPL']) > 0.0), (np.sum(data['SEMS'])/np.sum(data['SMPL'])), 0.0)
            
            # Call the capacity function
            # Calculate levelised cost again
            data = get_lcos(data, titles)
            ftt_s_fuel_consumption(data['BSTC'], data['SEWG'], data['SMED'], len(titles['RTI']), len(titles['STTI']), c5ti, len(titles['JTI']))
            
                

#         # Useful energy demand by boilers
#         # The historical data contains final energy demand
#         data['SEWG'][:, :, 0] = data['HEWF'][:, :, 0] * data['BHTC'][:, :, c5ti["9 Conversion efficiency"]]

#         for r in range(len(titles['RTI'])):

#             # Total useful heat demand
#             # This is the demand driver for FTT:Heat
#             #data['RHUD'][r, 0, 0] = np.sum(data['HEWG'][r, :, 0])

#             if data['RHUD'][r, 0, 0] > 0.0:

#                 # Market shares (based on useful energy demand)
#                 data['HEWS'][r, :, 0] = data['HEWG'][r, :, 0] / data['RHUD'][r, 0, 0]
#                 # Shares of final energy demand (without electricity)
#                 #data['HESR'][:, :, 0] = copy.deepcopy(data['HEWF'][:, :, 0])
#                 #data['HESR'][r, :, 0] = data['HEWF'][r, :, 0] * data['BHTC'][r, :, c4ti["19 RES calc"]] / np.sum(data['HEWF'] * data['BHTC'][r, :, c4ti["19 RES calc"]])

#                 # CORRECTION TO MARKET SHARES
#                 # Sometimes historical market shares do not add up to 1.0
#                 if (~np.isclose(np.sum(data['HEWS'][r, :, 0]), 0.0, atol=1e-9)
#                         and np.sum(data['HEWS'][r, :, 0]) > 0.0 ):
#                     data['HEWS'][r, :, 0] = np.divide(data['HEWS'][r, :, 0],
#                                                        np.sum(data['HEWS'][r, :, 0]))
                    
#             # Normalise HEWG to RHUD
#             data['HEWG'][r, :, 0] = data['HEWS'][r, :, 0] * data['RHUD'][r, 0, 0]
        
#         # Recalculate HEWF based on RHUD
#         data['HEWF'][:, :, 0] = data['HEWG'][:, :, 0] / data['BHTC'][:, :, c4ti["9 Conversion efficiency"]]

#         # Capacity by boiler
#         #Capacity (GW) (13th are capacity factors (MWh/kW=GWh/MW, therefore /1000)
#         data['HEWK'][:, :, 0] = divide(data['HEWG'][:, :, 0],
#                                 data['BHTC'][:, :, c4ti["13 Capacity factor mean"]])/1000
        
#         # Emissions
#         data['HEWE'][:, :, 0] = data['HEWF'][:, :, 0] * data['BHTC'][:, :, c4ti["15 Emission factor"]] / 1e6

#         for r in range(len(titles['RTI'])):
#             # Final energy demand by energy carrier
#             for fuel in range(len(titles['JTI'])):
#                 # Fuel use for heating
#                 data['HJHF'][r, fuel, 0] = np.sum(data['HEWF'][r, :, 0] * data['HJET'][0, :, fuel])
#                 # Fuel use for total residential sector
#                 if data['HJFC'][r, fuel, 0] > 0.0:
#                     data['HJEF'][r, fuel, 0] = data['HJHF'][r, fuel, 0] / data['HJFC'][r, fuel, 0]

#         # Investment (= capacity additions) by technology (in GW/y)
#         if year > 2014:
#             data["SEWI"][:, :, 0] = ((data["HEWK"][:, :, 0] - time_lag["HEWK"][:, :, 0])
#                                         + time_lag["HEWK"][:, :, 0] * data["HETR"][:, :, 0])
#             # Prevent SEWI from going negative
#             data['SEWI'][:, :, 0] = np.where(data['SEWI'][:, :, 0] < 0.0,
#                                                 0.0,
#                                                 data['SEWI'][:, :, 0])
            
#             bi = np.zeros((len(titles['RTI']), len(titles['HTTI'])))
#             for r in range(len(titles['RTI'])):
#                 bi[r,:] = np.matmul(data['HEWB'][0, :, :], data['SEWI'][r, :, 0])
#             dw = np.sum(bi, axis=0)
#             data['HEWW'][0, :, 0] = time_lag['HEWW'][0, :, 0] + dw

#     if year == histend['HEWF']:
#         # Historical data ends in 2020, so we need to initialise data
#         # when it's 2021 to make sure the model runs.

#         # If switch is set to 1, then an exogenous price rate is used
#         # Otherwise, the price rates are set to endogenous

#         #data['HFPR'][:, :, 0] = copy.deepcopy(data['HFFC'][:, :, 0])

#         # Now transform price rates by fuel to price rates by boiler
#         #data['HEWP'][:, :, 0] = np.matmul(data['HFFC'][:, :, 0], data['HJET'][0, :, :].T)

#         for r in range(len(titles['RTI'])):

#             # Final energy demand by energy carrier
#             for fuel in range(len(titles['JTI'])):

#                 # Fuel use for heating
#                 data['HJHF'][r, fuel, 0] = np.sum(data['HEWF'][r, :, 0] * data['HJET'][0, :, fuel])

#                 # Fuel use for total residential sector #HFUX is missing
#                 if data['HJFC'][r, fuel, 0] > 0.0:
#                     data['HJEF'][r, fuel, 0] = data['HJHF'][r, fuel, 0] / data['HJFC'][r, fuel, 0]

#         # Calculate the LCOT for each vehicle type.
#         # Call the function
#         data = get_lcos(data, titles)

# # %% Simulation of stock and energy specs
# #    t0 = time.time()
#     # Stock based solutions first
# #    if np.any(specs[sector] < 5):

#     # Endogenous calculation takes over from here
#     if year > histend['HEWF']:

#         

        
#         # Create the regulation variable
#         # Test that proved that the implimination of tanh across python and fortran is different
#         #for r in range (len(titles['RTI'])):
#             #for b in range (len(titles['HTTI'])):

#                 #if data['HREG'][r, b, 0] > 0.0:
#                     #data['HREG'][r, b, 0] = -1.0

#         division = divide((time_lag['HEWS'][:, :, 0] - data['HREG'][:, :, 0]),
#                            data['HREG'][:, :, 0]) # 0 if dividing by 0
#         isReg = 0.5 + 0.5 * np.tanh(1.5 + 10 * division)
#         isReg[data['HREG'][:, :, 0] == 0.0] = 1.0
#         isReg[data['HREG'][:, :, 0] == -1.0] = 0.0
    
        #  # Factor used to create quarterly data from annual figures
        #  no_it = int(data['noit'][0, 0, 0])
        #     dt = 1 / float(no_it)

#         ############## Computing new shares ##################

#         #Start the computation of shares
#         for t in range(1, no_it+1):

#             # Interpolate to prevent staircase profile.
#             rhudt = time_lag['RHUD'][:, :, :] + (data['RHUD'][:, :, :] - time_lag['RHUD'][:, :, :]) * t * dt
#             rhudlt = time_lag['RHUD'][:, :, :] + (data['RHUD'][:, :, :] - time_lag['RHUD'][:, :, :]) * (t-1) * dt

#             endo_eol = np.zeros((len(titles['RTI']), len(titles['HTTI'])))

#             for r in range(len(titles['RTI'])):

#                 if rhudt[r] == 0.0:
#                     continue

#             ############################ FTT ##################################
# #                        t3 = time.time()
# #                        print("Solving {}".format(titles["RTI"][r]))
#                 # Initialise variables related to market share dynamics
#                 # DSiK contains the change in shares
#                 dSik = np.zeros([len(titles['HTTI']), len(titles['HTTI'])])

#                 # F contains the preferences
#                 F = np.ones([len(titles['HTTI']), len(titles['HTTI'])]) * 0.5

#                 # -----------------------------------------------------
#                 # Step 1: Endogenous EOL replacements
#                 # -----------------------------------------------------
#                 for b1 in range(len(titles['HTTI'])):

#                     if  not (data_dt['HEWS'][r, b1, 0] > 0.0 and
#                              data_dt['HGC1'][r, b1, 0] != 0.0 and
#                              data_dt['HWCD'][r, b1, 0] != 0.0):
#                         continue

#                     S_i = data_dt['HEWS'][r, b1, 0]

#                     for b2 in range(b1):

#                         if  not (data_dt['HEWS'][r, b2, 0] > 0.0 and
#                                  data_dt['HGC1'][r, b2, 0] != 0.0 and
#                                  data_dt['HWCD'][r, b2, 0] != 0.0):
#                             continue

#                         S_k = data_dt['HEWS'][r, b2, 0]

#                         # Propagating width of variations in perceived costs
#                         dFik = 1.414 * sqrt((data_dt['HWCD'][r, b1, 0] * data_dt['HWCD'][r, b1, 0] 
#                                              + data_dt['HWCD'][r, b2, 0] * data_dt['HWCD'][r, b2, 0]))

#                         # Consumer preference incl. uncertainty
#                         Fik = 0.5 * (1 + np.tanh(1.25 * (data_dt['HGC1'][r, b2, 0]
#                                                    - data_dt['HGC1'][r, b1, 0]) / dFik))

#                         # Preferences are then adjusted for regulations
#                         F[b1, b2] = Fik * (1.0 - isReg[r, b1]) * (1.0 - isReg[r, b2]) + isReg[r, b2] \
#                                     * (1.0 - isReg[r, b1]) + 0.5 * (isReg[r, b1] * isReg[r, b2])
#                         F[b2, b1] = (1.0 - Fik) * (1.0 - isReg[r, b2]) * (1.0 - isReg[r, b1]) + isReg[r, b1] \
#                                     * (1.0 - isReg[r, b2]) + 0.5 * (isReg[r, b2] * isReg[r, b1])

#                         #Runge-Kutta market share dynamiccs
#                         k_1 = S_i*S_k * (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])
#                         k_2 = (S_i+dt*k_1/2)*(S_k-dt*k_1/2)* (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])
#                         k_3 = (S_i+dt*k_2/2)*(S_k-dt*k_2/2) * (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])
#                         k_4 = (S_i+dt*k_3)*(S_k-dt*k_3) * (data['HEWA'][0,b1, b2]*F[b1,b2]*data['HETR'][r,b2, 0]- data['HEWA'][0,b2, b1]*F[b2,b1]*data['HETR'][r,b1, 0])

#                         dSik[b1, b2] = dt*(k_1+2*k_2+2*k_3+k_4)/6
#                         dSik[b2, b1] = -dSik[b1, b2]

#                 # -----------------------------------------------------
#                 # Step 2: Endogenous premature replacements
#                 # -----------------------------------------------------
#                 # Initialise variables related to market share dynamics
#                 # DSiK contains the change in shares
#                 dSEik = np.zeros([len(titles['HTTI']), len(titles['HTTI'])])

#                 # F contains the preferences
#                 FE = np.ones([len(titles['HTTI']), len(titles['HTTI'])])*0.5

#                 # Intermediate shares: add the EoL effects before continuing
#                 # intermediate_shares = data_dt['HEWS'][r, :, 0] + np.sum(dSik, axis=1)

#                 # Scrappage rate
#                 SR = divide(np.ones(len(titles['HTTI'])),
#                             data['BHTC'][r, :, c4ti["16 Payback time, mean"]]) - data['HETR'][r, :, 0]
#                 SR = np.where(SR<0.0, 0.0, SR)

#                 for b1 in range(len(titles['HTTI'])):

#                     if not (data_dt['HEWS'][r, b1, 0] > 0.0 and
#                             data_dt['HGC2'][r, b1, 0] != 0.0 and
#                             data_dt['HGD2'][r, b1, 0] != 0.0 and
#                             data_dt['HGC3'][r, b1, 0] != 0.0 and
#                             data_dt['HGD3'][r, b1, 0] != 0.0 and
#                             SR[b1] > 0.0):
#                         continue

#                     SE_i = data_dt['HEWS'][r, b1, 0]

#                     for b2 in range(b1):

#                         if not (data_dt['HEWS'][r, b2, 0] > 0.0 and
#                                 data_dt['HGC2'][r, b2, 0] != 0.0 and
#                                 data_dt['HGD2'][r, b2, 0] != 0.0 and
#                                 data_dt['HGC3'][r, b2, 0] != 0.0 and
#                                 data_dt['HGD3'][r, b2, 0] != 0.0 and
#                                 SR[b2] > 0.0):
#                             continue

#                         SE_k = data_dt['HEWS'][r, b2, 0]

#                         # NOTE: Premature replacements are optional for
#                         # consumers. It is possible that NO premature
#                         # replacements take place

#                         # Propagating width of variations in perceived costs
#                         dFEik = 1.414 * sqrt((data_dt['HGD3'][r, b1, 0]*data_dt['HGD3'][r, b1, 0] + data_dt['HGD2'][r, b2, 0]*data_dt['HGD2'][r, b2, 0]))
#                         dFEki = 1.414 * sqrt((data_dt['HGD2'][r, b1, 0]*data_dt['HGD2'][r, b1, 0] + data_dt['HGD3'][r, b2, 0]*data_dt['HGD3'][r, b2, 0]))

#                         # Consumer preference incl. uncertainty
#                         FEik = 0.5*(1+np.tanh(1.25*(data_dt['HGC2'][r, b2, 0]-data_dt['HGC3'][r, b1, 0])/dFEik))
#                         FEki = 0.5*(1+np.tanh(1.25*(data_dt['HGC2'][r, b1, 0]-data_dt['HGC3'][r, b2, 0])/dFEki))

#                         # Preferences are then adjusted for regulations
#                         FE[b1, b2] = FEik*(1.0-isReg[r, b1])
#                         FE[b2, b1] = FEki*(1.0-isReg[r, b2])

#                         #Runge-Kutta market share dynamiccs
#                         kE_1 = SE_i*SE_k * (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])
#                         kE_2 = (SE_i+dt*kE_1/2)*(SE_k-dt*kE_1/2)* (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])
#                         kE_3 = (SE_i+dt*kE_2/2)*(SE_k-dt*kE_2/2) * (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])
#                         kE_4 = (SE_i+dt*kE_3)*(SE_k-dt*kE_3) * (data['HEWA'][0,b1, b2]*FE[b1,b2]*SR[b2]- data['HEWA'][0,b2, b1]*FE[b2,b1]*SR[b1])

#                         dSEik[b1, b2] = dt*(kE_1+2*kE_2+2*kE_3+kE_4)/6
#                         dSEik[b2, b1] = -dSEik[b1, b2]

#                 #calculate temportary market shares and temporary capacity from endogenous results
#                 endo_shares = data_dt['HEWS'][r, :, 0] + np.sum(dSik, axis=1) + np.sum(dSEik, axis=1)
                
#                 endo_capacity = endo_shares * rhudt[r, np.newaxis]/data['BHTC'][r, :, c4ti["13 Capacity factor mean"]]/1000

#                 endo_gen = endo_shares * rhudt[r, np.newaxis]

#                 endo_eol[r] = np.sum(dSik, axis=1)

#                 # -----------------------------------------------------
#                 # Step 3: Exogenous sales additions
#                 # -----------------------------------------------------
#                 # Add in exogenous sales figures. These are blended with
#                 # endogenous result! Note that it's different from the
#                 # ExogSales specification!
#                 Utot = rhudt[r]
#                 dSk = np.zeros([len(titles['HTTI'])])
#                 dUk = np.zeros([len(titles['HTTI'])])
#                 dUkTK = np.zeros([len(titles['HTTI'])])
#                 dUkREG = np.zeros([len(titles['HTTI'])])

#                 # Note, as in FTT: H shares are shares of generation, corrections MUST be done in terms of generation. Otherwise, the corrections won't line up with the market shares.


#                 # Convert exogenous shares to exogenous generation. Exogenous sharess no longer need to add up to 1. Beware removals!
#                 for b in range (len(titles['HTTI'])):
#                     if data['HWSA'][r, b, 0] < 0.0:
#                         data['HWSA'][r, b, 0] = 0.0
                
#                 dUkTK = data['HWSA'][r, :, 0]*Utot/no_it

#                 # Check endogenous shares plus additions for a single time step does not exceed regulated shares
#                 reg_vs_exog = ((data['HWSA'][r, :, 0]*Utot/no_it + endo_gen) > data['HREG'][r, :, 0]*Utot) & (data['HREG'][r, :, 0] >= 0.0)
#                 # Filter capacity additions based on regulated shares
#                 dUkTK = np.where(reg_vs_exog, 0.0, dUkTK)


#                 # Correct for regulations due to the stretching effect. This is the difference in generation due only to demand increasing.
#                 # This will be the difference between generation based on the endogenous generation, and what the endogenous generation would have been
#                 # if total demand had not grown.

#                 dUkREG = -(endo_gen - endo_shares * rhudlt[r,np.newaxis]) * isReg[r, :].reshape([len(titles['HTTI'])])
                     

#                 # Sum effect of exogenous sales additions (if any) with
#                 # effect of regulations
#                 dUk = dUkREG + dUkTK
#                 dUtot = np.sum(dUk)

  
#                 # Calaculate changes to endogenous generation, and use to find new market shares
#                 # Zero generation will result in zero shares
#                 # All other capacities will be streched

#                 if (np.sum(endo_gen) + dUtot) > 0.0:
#                     data['HEWS'][r, :, 0] = (endo_gen + dUk)/(np.sum(endo_gen)+dUtot)

#                 #print("Year:", year)
#                 #print("Region:", titles['RTI'][r])
#                 #print("Sum of market shares:", np.sum(data['HEWS'][r, :, 0]))

#                 if ~np.isclose(np.sum(data['HEWS'][r, :, 0]), 1.0, atol=1e-2):
#                     msg = """Sector: {} - Region: {} - Year: {}
#                     Sum of market shares do not add to 1.0 (instead: {})
#                     """.format(sector, titles['RTI'][r], year, np.sum(data['HEWS'][r, :, 0]))
#                     warnings.warn(msg)

#                 if np.any(data['HEWS'][r, :, 0] < 0.0):
#                     msg = """Sector: {} - Region: {} - Year: {}
#                     Negative market shares detected! Critical error!
#                     """.format(sector, titles['RTI'][r], year)
#                     warnings.warn(msg)
# #                        t4 = time.time()
# #                        print("Share equation takes {}".format(t4-t3))

#             ############## Update variables ##################
#             # Useful heat by boiler
#             data['HEWG'][:, :, 0] = data['HEWS'][:, :, 0] * rhudt[:, 0, 0, np.newaxis]

#             # Final energy by boiler
#             data['HEWF'][:, :, 0] = divide(data['HEWG'][:, :, 0],
#                                              data['BHTC'][:, :, c4ti["9 Conversion efficiency"]])

#             # Capacity by boiler
#             data['HEWK'][:, :, 0] = divide(data['HEWG'][:, :, 0],
#                                               data['BHTC'][:, :, c4ti["13 Capacity factor mean"]])/1000

#             # EmissionsFis
#             data['HEWE'][:, :, 0] = data['HEWF'][:, :, 0] * data['BHTC'][:, :, c4ti["15 Emission factor"]]/1e6

#             # TODO: HEWP = HFPR not HFFC
#             #data['HFPR'][:, :, 0] = copy.deepcopy(data['HFFC'][:, :, 0])

#             data['HEWP'][:, 0, 0] = data['HFFC'][:, 4, 0]
#             data['HEWP'][:, 1, 0] = data['HFFC'][:, 4, 0]
#             data['HEWP'][:, 2, 0] = data['HFFC'][:, 6, 0]
#             data['HEWP'][:, 3, 0] = data['HFFC'][:, 6, 0]
#             data['HEWP'][:, 4, 0] = data['HFFC'][:, 10, 0]
#             data['HEWP'][:, 5, 0] = data['HFFC'][:, 10, 0]
#             data['HEWP'][:, 6, 0] = data['HFFC'][:, 0, 0]
#             data['HEWP'][:, 7, 0] = data['HFFC'][:, 8, 0]
#             data['HEWP'][:, 8, 0] = data['HFFC'][:, 7, 0]
#             data['HEWP'][:, 9, 0] = data['HFFC'][:, 7, 0]
#             data['HEWP'][:, 10, 0] = data['HFFC'][:, 7, 0]
#             data['HEWP'][:, 11, 0] = data['HFFC'][:, 7, 0]

#             # Final energy demand for heating purposes
#             data['HJHF'][:, :, 0] = np.matmul(data['HEWF'][:, :, 0], data['HJET'][0, :, :])

#             # Final energy demand of the residential sector (incl. non-heat)
#             # For the time being, this is calculated as a simply scale-up
#             for fuel in range(len(titles['JTI'])):
#                 if data['HJFC'][r, fuel, 0] > 0.0:
#                     data['HJEF'][r, fuel, 0] = data['HJHF'][r, fuel, 0] / data['HJFC'][r, fuel, 0]

             

            #  =================================================================
            # Update the time-loop variables
            # =================================================================

            #Update time loop variables:
            for var in data_dt.keys():

                data_dt[var] = copy.deepcopy(data[var])


    return data
