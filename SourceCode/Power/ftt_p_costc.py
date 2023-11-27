'''
=========================================
ftt_p_costc.py
=========================================
Power cost-supply curves module.
################################

Cost-supply curves give the cost of a resource as a function of its quantity, and
hence provide the **marginal cost** of each resource. For example, if a fossil fuel
resource is running out, the fuel cost increases. For e.g. hydropower, if there are
less accessible places to build, then the investment cost goes up. For variable
renewables, the load factor (the number of hours it delivers to the grid, divide by the
number of hours in a year).


Functions included:
    - interp
        Iterpolation function
    - marginal_function
        Calculates marginal cost of production of non renewable resources
    - cost_curves
        Calculates cost-supply curves for the power sector


.. note::
   For correspondance with E3ME:
   NR is rti, NT2 is t2ti, NJ is jti, NER is erti, NM is mti, NC2 is c2ti

'''
# Standard library imports
from math import sqrt
import os
import copy
import sys
import warnings

# Third party imports
import pandas as pd
import numpy as np
from numba import njit

# Local library imports
from SourceCode.support.divide import divide

# %% interpolation function
# -----------------------------------------------------------------------------
# -------------------------- Interpolate ------------------------------
# -----------------------------------------------------------------------------

def interp(X,Y,X0,L):
    '''

    Linear interpolation function which estimates data points between start points
    and end points.


    Parameters
    -----------
    X: List
        X vector for interpolation
    Y: List
        Y vector for interpolation
    X0: float
        Value at which to interpolate
    L: int
        Length of data set



    Returns
    ----------
    Y0: float
        Interpolated value
    I: int
        Index of the position of the interpolated value


    '''
    # So that we don't change the incoming L
    LL = L/2
    # X Data spacing: assumes homogenous spacing
    D = abs(X[1]-X[0])
    # We do a table lookup algorithm
    I = int(LL)
    while abs(X[I]-X0) > D:
        LL = LL/2
        if(X[I] > X0):
            I = I - max(int(LL),1)    # int() truncates decimals and converts to an integer
        else:
            I = I + max(int(LL),1)
        # These conditionals refer to cases where X0 falls outside of X
        if(I == 0):
            I = 1
            break
        elif(I == L-1):
            I = L-1
            break

#    if I > X.shape[0]:
#        print("stop")
    if(X0 < X[I] and I > 1):
        X1 = X[I-1]
        Y1 = Y[I-1]
        X2 = X[I]
        Y2 = Y[I]
        # Interpolate linearly between (X1,Y1) and (X2,Y2) at X0
        Y0 = Y1 + (Y2-Y1)*(X0-X1)/(X2-X1)
    elif (X0 >= X[I] and I < L-1):
        X1 = X[I]
        Y1 = Y[I]
        X2 = X[I+1]
        Y2 = Y[I+1]
        # Interpolate linearly between (X1,Y1) and (X2,Y2) at X0
        Y0 = Y1 + (Y2-Y1)*(X0-X1)/(X2-X1)
    elif(X0 < X[I] and I == 1):  # If X0 is below the range we take the last value
        Y0 = Y[1]
    elif(X0 > X[I] and I == L-1):  # If X0 is above the range
        Y0 = Y[L-1]

    return Y0, I

# %% marginal cost of production of non renewable resources
# -----------------------------------------------------------------------------
# -------------------------- marginal calculation ------------------------------
# -----------------------------------------------------------------------------
def marginal_function(MEPD,RERY,MPTR,BCSC,HistC,MRCL,MERC,MRED,MRES,rti,erti,year,dt,MERCX):
    '''
    Marginal cost of production of non renewable resources.

    Parameters
    -----------
      MPTR: NumPy array
        Values of nu by region (Production to reserve ratio) See paper Mercure & Salas arXiv:1209.0708 for data
      HistC: NumPy array
        Cost axis C
      MRCL: NumPy array
        Previous marginal cost value
      MEPD: NumPy array
        Total resource demand
      MERC: NumPy array
        Current (new) marginal cost value
      MRED: NumPy array
        Resources left
      MRES: NumPy array
        reserves
      RERY: NumPy array
        supply in GJ of fossil fuel resource (only I = 2 to 4 used)
      BCSC: NumPy array
        Dataset for natural resources
      rti: int
        Length of regional titles
      t2ti: int
        Length of technology titles



    Returns
    ----------
      RERY
      BCSC
      HistC
      MERC
      MRED
      MRES

    '''
    L = 990
    MRED = np.zeros([71,14,1])
    MRES = np.zeros([71,14,1])
    P = np.zeros([4])
    D = np.zeros([4])
    #dQdt = np.zeros([990])
    tc = np.zeros([990])
    #dFdthold = np.zeros([990])
    # Values of nu: empirical production to reserve ratio (y^-1)
    # See paper Mercure & Salas arXiv:1209.0708 for data (Energy Policy 2013)
    #nu(1) = 1/16.0    #Uranium
    #nu(2) = 1/42.0    #Oil        (i.e. 42 years to deplete current reserves (not resources#))
    #nu(3) = 1/122.0   #Coal
    #nu(4) = 1/62.0    #Gas
    #Width of the F function is resource-dependent (exception made for coal where cost data is coarse)
    sig = np.zeros([4])
    sig[0] = 1       #Uranium
    sig[1] = 1       #Oil
    sig[2] = 1        #Coal
    sig[3] = 1       #Gas

    #First 4 elements are the non-renewable resources

    P[:4] = copy.deepcopy(MRCL[1,:4,0])  #All marginal costs of non-renewable resources are identical (global), we use 1-USA ? 1 is not USA
    MEPD_sum = np.sum(MEPD[:,:,0], axis=0) #sum over regions
    D[:4] = copy.deepcopy(MEPD_sum[:4])      #Global demand for non-renewable resources

    # We search for the value of P that enables enough total production to supply demand
    # i.e. the value of P that minimises the difference between dFdt and D
    for j in range(4): # j=0,1,2,3
        #Cost interval
        dC = HistC[j,1] - HistC[j,0]
        dFdt = 0
        count = 0
        while abs((dFdt-D[j])/D[j]) > 0.01  and count < 20:
            # Sum total supply dFdt from all extraction cost ranges below marginal cost P            dFdt = 0
            tc[:] = 0.5-0.5*np.tanh(1.25*2*sig[j]*divide(HistC[j,:]-P[j],P[j]))
            #tc = 0
            #WHERE (HistC(I,:) < P(I)) tc(:) = 1

            # for i in range(rti): THIS IS REWRITTEN BELOW
            #     dQdt = MPTR[i,j] * BCSC[i,j,4:] * tC #goes from 5 in fortran
            #     dFdthold[i] = sum(dQdt)*dC
            # dFdt= sum(dFdthold[1:rti])

            dFdt = np.sum(np.sum(MPTR[:,j,0].reshape((71,1)) * BCSC[:,j,4:] * tc.reshape((1,L))*dC, axis = 0))

            # Work out price
            # Difference between supply and demand
            if(dFdt < D[j]):
                # Increase the marginal cost
                P[j] = P[j]*(1.0+np.abs(dFdt-D[j])/D[j]/8)
            else:
                # Decrease the marginal cost
                P[j] = P[j]/(1.0+np.abs(dFdt-D[j])/D[j]/5)
            count = count + 1



        # Remove used resources from the regional histograms (uranium, oil, coal and gas only)
        # Have removed loop, should be the same
        # loop was over regions
        BCSC[:,j,4:] = BCSC[:,j,4:] - (MPTR[:,j,0].reshape((71,1))*BCSC[:,j,4:]*(0.5-0.5*np.tanh(1.25*2*sig[j]*divide(HistC[j,:]-P[j],P[j]))))*dt
        RERY[:,j,0] = np.sum((MPTR[:,j,0].reshape((71,1))*BCSC[:,j,4:]*(0.5-0.5*np.tanh(1.25*2*sig[j]*divide(HistC[j,:]-P[j],P[j]))))*dC)

        # Write back new marginal cost values (same value for all regions)

        MERC[:,j,0] = copy.deepcopy(P[j])
        MERC[:,j,0] = copy.deepcopy(MERCX[:,j,0])


        # for j in range(NR):
        #     for k in range(990):
        #         #sum resources. Note that the cost interval of the density distribution is dC = (BCSC(I,J,3)-BCSC(I,J,2))/(BCSC(I,J,4)-1)
        #         MRED[i,j] = MRED[i,j] + BCSC[i,j,4+K]*(BCSC[i,j,3]-BCSC[i,j,2])/(BCSC[i,j,4]-1)
        #         MRES[i,j] = MRES[i,j] + BCSC[i,j,4+K]*(BCSC[i,j,3]-BCSC[i,j,2])/(BCSC[i,j,4]-1)*(0.5-0.5*np.tanh(1.25*2*(HistC[i,k]-P[i])/P[i]))


        #sum resources. rewritten to remove loops
        HistCSUM = np.sum(HistC,axis=1)
        MRED[:,j,0] = MRED[:,j,0] + np.sum(BCSC[:,j,3:],axis=1)*(BCSC[:,j,2]-BCSC[:,j,1])/(BCSC[:,j,3]-1)
        MRES[:,j,0] = MRES[:,j,0] + np.sum(BCSC[:,j,3:],axis=1)*(BCSC[:,j,2]-BCSC[:,j,1])/(BCSC[:,j,3]-1)*(0.5-0.5*np.tanh(1.25*2*divide(HistCSUM[j]-P[j],P[j])))



    # Here we calculate how much non-renewable resources we have left in the cost curves
    return RERY,BCSC,HistC,MERC,MRED,MRES


# %% cost curves function
# -----------------------------------------------------------------------------
# -------------------------- Cost Curves ------------------------------
# -----------------------------------------------------------------------------
def cost_curves(BCET,BCTL,BCSC,MEWD,MEWG,MEWL,MEPD,MERC,MRCL,RERY,MPTR,PMF,MRED,MRES,mti,rti,t2ti,c2ti,jti,erti,year,dt,MERCX):
    '''FTT: Power cost-supply curves routine. This calculates the cost of resources given
    the available supply. '''

    lmo = np.asarray([i for i in range(990)]) #This will have length 990, from 0 to 989
    L=990
    CSC_Q = np.zeros([71,14,990])
    HistC = np.zeros([14,990])
    #HistQ = np.zeros([14,990])
    X = np.zeros([990])
    Y = np.zeros([990])
    Ind = 0
    CFvar = np.zeros([990])

    #Resources classification:
    #Correspondence vector between NT2 and NER (Technologies and resources: if I = Tech, II(I) = resource#)
    conv = [0, 1, 2, 2, 2, 2, 3, 3, 4, 4, 4, 4, 5, 6, 7, 8, 9, 10, 11, 11, 12, 13, 3, 3]

    #BCSC is natural resource data with dimensions NER NR and length of cost axis k

    # Unpack Histograms
    # First 4 values in each BCSC(I,J,:) vectors are:
    # Parameters: (1) Type (2) Min (3) Max (4) Number of data points
    # Resource data type: (1) Histogram, (2) Fuel cost, (3) Investment cost, (4) Capacity Factor reduction

    for i in range(len(erti)): #resource classification
        # if the data type contained in k=0 (k=1 in fortran) is a histogram (same for all regions)
        if (BCSC[0,i,0]==1):

            HistC[i,:] = BCSC[0,i,1]+lmo*(BCSC[0,i,2]-BCSC[0,i,1])/(BCSC[0,i,3]-1)
            #BCSC goes up to L+4, Hist goes up to L
            #HistQ[j,:] = HistQ[j,:] + sum(BCSC[:,j,4:], axis=0) #actual histograms, adds up regions, after 4 k is PJ/bin size (PJ/dollar), units sorted into bins are PJs of energy

        # type not histogram
        else:

            for j in range(len(rti)):

                #QuantityAxis(K) = min(Q) + (K-1)*(max(Q)-min(Q))/(N data points -1) #We don't need this loop either I believe
                CSC_Q[j,i,:] = BCSC[j,i,1] + lmo*(BCSC[j,i,2]-BCSC[j,i,1])/(BCSC[j,i,3]-1)


    #Calculate non-renewable resource use
    #Non renewable resource use (treated global <=> identical for all regions)

    #Sum electricity generation for all regions, transform into PJ (resource histograms in PJ)
    #MEWD is the non-power demand for resources
    #RERY is set in FTTinvP for fossil fuels

    #Uranium
    MEPD[:,0,0] = divide(MEWG[:,0,0], BCET[:,0,13])*3.6/1000
    #Oil
    MEPD[:,1,0] = MEWD[:,2,0] + MEWD[:,3,0] + MEWD[:,4,0]
    #Coal
    MEPD[:,2,0] = MEWD[:,0,0] + MEWD[:,1,0]
    #Gas
    MEPD[:,3,0] = copy.deepcopy(MEWD[:,6,0])

    #Renewable resource use is local, so equal to MEPD [we assume RERY equal to MEPD regionally, although it is globally):
    #Biomass [the cost curve is in PJ)
    MEPD[:,4,0] = (divide(MEWG[:,8,0],BCET[:,8,13])+divide(MEWG[:,9,0],BCET[:,9,13])+divide(MEWG[:,10,0],BCET[:,10,13])+divide(MEWG[:,11,0],BCET[:,11,13]))*3.6/1000 #+ MEWD[11,:] + MEWD[10,:]
    RERY[:,4,0] = copy.deepcopy(MEPD[:,4,0]) #in PJ
    #Biogas (From here onwards cost curves are in TWh)
    MEPD[:,5,0] = (MEWG[:,12,0]+MEWG[:,13,0]*divide(BCET[:,13,13],BCET[:,12,13]))*3.6/1000
    RERY[:,5,0] = copy.deepcopy(MEPD[:,5,0]) # in PJ
    #Biogas + CCS
    MEPD[:,6,0] = (MEWG[:,12,0]+MEWG[:,13,0]*divide(BCET[:,13,13],BCET[:,12,13]))*3.6/1000
    RERY[:,6,0] = copy.deepcopy(MEPD[:,6,0]) # in PJ
    #Tidal
    MEPD[:,7,0] = MEWG[:,14,0]*3.6/1000
    RERY[:,7,0] = copy.deepcopy(MEPD[:,7,0]) # in PJ
    #Hydro
    MEPD[:,8,0] = MEWG[:,15,0]*3.6/1000
    RERY[:,8,0] = copy.deepcopy(MEPD[:,8,0]) # in PJ
    #Onshore
    MEPD[:,9,0] = MEWG[:,16,0]*3.6/1000
    RERY[:,9,0] = copy.deepcopy(MEPD[:,9,0]) # in PJ
    #Offshore
    MEPD[:,10,0] = MEWG[:,17,0]*3.6/1000
    RERY[:,10,0] = copy.deepcopy(MEPD[:,10,0]) # in PJ
    #Solar (PV + CSP)
    MEPD[:,11,0] = (divide(MEWG[:,18,0],BCET[:,18,13]) + divide(MEWG[:,19,0],BCET[:,19,13]))*3.6/1000
    RERY[:,11,0] = copy.deepcopy(MEPD[:,11,0]) # in PJ
    #Geothermal
    MEPD[:,12,0] = MEWG[:,20,0]*3.6/1000
    RERY[:,12,0] = copy.deepcopy(MEPD[:,12,0]) # in PJ
    #Wave
    MEPD[:,13,0] = MEWG[:,21,0]*3.6/1000
    RERY[:,13,0] = copy.deepcopy(MEPD[:,13,0]) # in PJ

    #All regions have the same information
    MERC[:,0,0] = copy.deepcopy(MRCL[:,0,0])
    MERC[:,1,0] = copy.deepcopy(MRCL[:,1,0])
    MERC[:,2,0] = copy.deepcopy(MRCL[:,2,0])
    MERC[:,3,0] = copy.deepcopy(MRCL[:,3,0])
    MERC[:,4,0] = copy.deepcopy(MRCL[:,4,0])


    # Before 2017 do not overwrite RERY for fossil fuels, and no need to calculate CSCurves
    if(year <= 2013):
        return BCET, BCSC, MEWL, MEPD, MERC, RERY, MRED, MRES

    # Calculate the marginal cost of production of non renewable resources
    if(year >= 2017):

        RERY,BCSC,HistC,MERC,MRED,MRES = marginal_function(MEPD,RERY,MPTR,BCSC,HistC,MRCL,MERC,MRED,MRES,rti,erti,year,dt,MERCX)


    # Update costs in the technology cost matrix BCET (BCET(:,:,12) is the type of cost curve)
    for i in range(len(rti)):
        for j in range(len(t2ti)):
            if(MEPD[i,conv[j]] > 0.0):

                #Non-renewable resources fuel costs (histograms)
                if(BCET[i,j,11]==1):

                    BCET[i,j,4] = BCET[i,j,4] + (MERC[i,conv[j],0] - MRCL[i,conv[j],0])*3.6/BCET[i,j,13]
                    BCET[i,j,4] = BCET[i,j,4] + (MERCX[i,conv[j],0] - MRCL[i,conv[j],0])*3.6/BCET[i,j,13]

                #For renewable resources: interpolate MEPD into the cost curves. Decreasing capacity factor type of limit
                elif(BCET[i,j,11]==0):

                    X = copy.deepcopy(CSC_Q[i,conv[j],:])
                    Y = copy.deepcopy(BCSC[i,conv[j],4:])

                    # Note: the curve is in the form of an inverse capacity factor in BCSC
                    X0 = MEPD[i,conv[j],0]/3.6 #PJ -> TWh
                    if(X0> 0.0): Y0, Ind = interp(X,Y,X0,L)
                    MERC[i,conv[j],0] = 1.0/(Y0+0.000001)
                    # TODO: SET Exog MERC
                    MERC[i,conv[j],0] = copy.deepcopy(MERCX[i,conv[j],0])
                    BCET[i,j,10] = 1.0/(Y0+0.000001)         # We use an inverse here
                    BCET[i,j,10] = copy.deepcopy(MERCX[i,conv[j],0])
                    # For variable renewables (e.g. wind, solar, wave)
                    # the overall (average) capacity factor decreases as new units have lower and lower CFs

                    if(MEWG[i,j,0] > 0.01 and Ind > 1 and X0 > 0):

                        # Average capacity factor costs up to the point of use (integrate CSCurve divided by total use)
                        CFvar[1:Ind+1] = 1.0/(Y[1:Ind+1]+0.000001)/(Ind)
                        if(sum(CFvar[1:Ind+1]) > 0):

                            MEWL[i,j,0] = sum(CFvar[1:Ind+1])


                    #Fix: CSP is more efficient than PV by a factor 2
                    BCET[i,19,10] = 1.0/(Y0+0.0000001)*2.0

                    BCET[i,19,10] = MERCX[i,conv[j],0] * 2.0

                #Increasing investment term type of limit
                elif(BCET[i,j,11] == 3):

                    #------> Insert an interpolation here TODO this is from the fortran, do I need to do this?
                    X = copy.deepcopy(CSC_Q[i,conv[j],:])
                    Y = copy.deepcopy(BCSC[i,conv[j],4:])

                    X0 = MEPD[i,conv[j],0]/3.6 #PJ -> TWh
                    if(X0> 0.0): Y0, I = interp(X,Y,X0,L)
                    MERC[i,conv[j],0] = copy.deepcopy(Y0)
                    # TODO: SET Exog MERC
                    MERC[i,conv[j],0] = copy.deepcopy(MERCX[i,conv[j],0])
                    BCET[i,j,2] = copy.deepcopy(Y0)
                    BCET[i,j,2] = copy.deepcopy(MERCX[i,conv[j],0])

    #Add REN resources left in MRED, MRES
    #Total technical potential i>4 (j>4 in python)
    MRED[:,4:,0] = copy.deepcopy(BCSC[:,4:,2])
    #Remaining technical potential
    MRES[:,4:,0] = BCSC[:,4:,2] - MEPD[:,4:,0]

    return BCET, BCSC, MEWL, MEPD, MERC, RERY, MRED, MRES
