# -*- coding: utf-8 -*-
"""
NB this may not always work due to two competeing contrainsts which can not always both be true at the same time. 
The first is that the shares must add up to one; the second is that the rate of change of shares must be constant accross the boundary. 

Rosie Hayward, Created 09/05/2023

An algorithm for finding the gamma values used in FTT simulations. This algorithm should find the values of gamma such that
the sign of the gradient (dS/dt, the rate of change of shares) becomes the same across the boundary.

This is a relaxed condition, with the true condition being that the rate of change of shares should be constant across the 
boundary between the historical and simulated period. 

The levelised costs do not currently change in this test code, however as learning is not likely to be vast over a period of five years, 
the code is able to produce reasonable results. 

This algorithm calculates the market shares for a single data set, the rate of change of market shares, and the rate of change of historical shares.
A function known as gradient_ratio then calculates the ratio of the simulated rate of change to the historical rate of change.

"""
from pylab import *

import numpy as np
import pandas as pd
import math


Shares = pd.read_csv("Gamma Value Automation/IWS1_AT.csv", index_col = 0)
S_h = Shares.iloc[:,11:16].values
Costs = pd.read_csv("Gamma Value Automation/costs.csv", index_col = 0)
dC = Costs.iloc[:,1].values
C = Costs.iloc[:,0].values

A = pd.read_csv("Gamma Value Automation/IWA1.csv", index_col = 0).values


gamma=pd.read_csv("Gamma Value Automation/IAM1_AT.csv", index_col = 0)
gamma = 0.00*gamma.iloc[:,0].values


print(S_h)
print(gamma)



N=len(C)

def sdij(dC_1, dC_2):
    sdij_ = sqrt(2)*sqrt(dC_1*dC_1 + dC_2*dC_2)
    return sdij_


def Fij(C_1,C_2, gamma_1, gamma_2, dC_1, dC_2):
    Fij_=0.5*(1+np.tanh(5*(C_2*(1+gamma_2)-C_1*(1+gamma_1))/(4*sdij(dC_1, dC_2))))
    return Fij_



#Need to define future shares as a function
def S_f(gamma, S_h, A, C, dC,N):
    
    S = np.zeros([N,5])
    S[:,0] = S_h[:,4]

    for t in range(1,5):
        S[:,t] = S[:,t-1].copy()
        for n in range(4):

            dS = np.zeros([N,N])

            for i in range(N):
                for j in range(N):
                    dS[i,j] = S[i][t]*S[j][t]*(A[i][j]*Fij(C[i],C[j], gamma[i], gamma[j], dC[i], dC[j])
                        -A[j][i]*Fij(C[j],C[i], gamma[j], gamma[i],  dC[j], dC[i]))*0.25
            S[:,t] = S[:,t] + dS.sum(axis=1)
        
    return S



#Sdot should only be calculated for the future period. For the historical period, we should estimate it using the historical data
def S_dot_f(gamma, S, A, C, dC,N):

    S_dot =  np.zeros([N,5])
 
    for t in range(4):

        for n in range(4):

            dS = np.zeros([N,N])

            for i in range(N):
                for j in range(N):
                    dS[i,j] = S[i][t]*S[j][t]*(A[i][j]*Fij(C[i],C[j], gamma[i], gamma[j], dC[i], dC[j])
                        -A[j][i]*Fij(C[j],C[i], gamma[j], gamma[i],  dC[j], dC[i]))*0.25
            S_dot[:,t] = dS.sum(axis=1)
    return S_dot





def S_dot_hist_f(S_h,N): #The historical rate of change of shares right before the boundary must be calculated.
    S_dot_hist=np.zeros(N)
    for i in range(N):
       
        S_dot_hist[i] = (S_h[i][4]-S_h[i][0])/5
    return S_dot_hist









def L_f(shar_dot, shar_dot_hist, N):
    L=np.zeros(N)
    shar_dot_avg = shar_dot.sum(axis=1)/5
    for i in range(N):
        if shar_dot_hist[i] == 0:
            L[i] = 0
        else:
            L[i] = shar_dot_avg[i]/shar_dot_hist[i]
    return L



'''
Core Routine (uses all functions)
'''
for iter in range(200):


    shares = S_f(gamma, S_h, A, C, dC,N)

    shar_dot = S_dot_f(gamma, shares, A, C, dC,N)

    shar_dot_hist = S_dot_hist_f(S_h, N)

    gradient_ratio = L_f(shar_dot, shar_dot_hist, N)

    for i in range(N):
        if gradient_ratio[i] < 0:
            if shar_dot_hist[i] < 0:
                gamma[i] += 0.01
            if shar_dot_hist[i] > 0:
                gamma[i] -= 0.01
        if gradient_ratio[i] > 0:
            if gradient_ratio[i] < 0.01:
                gamma[i] -= 0.01
            if gradient_ratio[i] > 100:
                gamma[i] += 0.01
        if gamma[i] > 1: gamma[i] = 1
        if gamma[i] < -1: gamma[i] = -1



print(gamma)




#space
