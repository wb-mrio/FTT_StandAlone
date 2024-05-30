# -*- coding: utf-8 -*-
"""
NB this code is unfinished and the functions do not currently work correctly

Rosie Hayward, Created 02/11/2021

An algorithm for finding the gamma values used in FTT simulations. This algorithm should find the values of gamma such that
the diffusion of shares is constant across the boundary between the historical and simulated period.
It uses the Newton-Raphson algorithm - a simple example of this can be found on the SVN.

Steps: For initial guesses of gamma values and lagged shares read-in from the model, calculate Sdot, L, and dL/dgamma, and run Newton-Raphson for all shares.
The equation which calculates the shares, Sdot, L, and dL/dgamma are all implicitly part of the NR algorithm and as gamma changes all these functions will be updated, so there
is no need to have separate 're-runs' of the model. i.e. out NR function we're trying to find the root of, L, is a function of S, which is also a function of gamma. S will be recalculated for every iteration.

Only one gamma value can change at a time, so we will need to cap the number of iterations, and move on to other gamma values when we think we've got closer to the root.
We will then need to re-loop, recalculating the first gamma value after all the others have changed, and so on.

Using FTT:Power as a first test:
- Historical shares need to read in
- Levelised cost need to be read in
- Aij need to be read in
- Gamma values need initial guesses

"""
from pylab import *

import numpy as np
import pandas as pd
import math



S=[] #Shares should be an array. A column will represent shares i to j. i or j will be used as the loop variable.
 #Historical shares need to be a separate array. Each column will represent shares i to j. Each row will represent the relevant time step. t will be used as the loop variable. These should be read in as exogeneous variables.
        #t_0 is the time just before the simulation begins - the last historical time step
t_0=2
t_1=1
t_2=0

#Aij will also be an array, with columns and rows both representing shares. It should be the Aij for the first time step of the simulation. Exogeneous.

#Fij can be defined as a function of the cost and the gamma values. Initial gamma values and the levilised costs should be read in externally.

#The levelised cost can be array in the same structure as the shares. Also exogeneous, as it is separate from gamma. It should be the cost used in the first calculation of the shares, that is the cost used in the first time step of the simulation.
#The levelised cost standard deviations/variations




Shares = pd.read_csv("IWS1_AT.csv", index_col = 0)
S_h = Shares.iloc[:,13:16].values
Costs = pd.read_csv("costs.csv", index_col = 0)
dC = Costs.iloc[:,1].values
C = Costs.iloc[:,0].values

A = pd.read_csv("A_Matrix.csv", index_col = 0).values
# TODO
# A = A/decom_rate axis = i, decom_rate = 1/lifetime
# A = A/replace rate axis = j, replace rate = 1/buildtime (leadtime?)

gamma=pd.read_csv("IAM1_AT.csv", index_col = 0)
gamma = 0.001*gamma.iloc[:,0].values


print(S_h)
print(gamma)


step_size = 1 #arbitray for now
N=len(C)

def sdij(dC_1, dC_2):
    sdij_ = sqrt(2)*sqrt(dC_1*dC_1 + dC_2*dC_2)
    return sdij_


def Fij(C_1,C_2, gamma_1, gamma_2, dC_1, dC_2):
    Fij_=0.5*(1+np.tanh(5*(C_1-C_2+gamma_1-gamma_2)/(4*sdij(dC_1, dC_2))))
    return Fij_

def diff_Fij(C_1,C_2, gamma_1, gamma_2,  dC_1, dC_2):
    diff_Fij_=2.5*((1/np.cosh(5*(C_1-C_2+gamma_1-gamma_2)/(4*sdij(dC_1, dC_2))))**2)/(4*sdij(dC_1, dC_2))
    return diff_Fij_

#Need to define future shares as a function
def S_f(gamma, S_h, A, C, dC,N, step_size):
    dS = np.zeros(N)
    S = np.zeros(N)
    for i in range(N):
        for j in range(N):
            dS[i] =  dS[i] + S_h[i][t_0]*S_h[j][t_0]*(A[i][j]*Fij(C[i],C[j], gamma[i], gamma[j], dC[i], dC[j])
                -A[j][i]*Fij(C[j],C[i], gamma[j], gamma[i],  dC[j], dC[i]))*step_size
    S = S_h[:,t_0] + dS
    return S



#Sdot should only be calculated for the future period. For the historical period, we should estimate it using the historical data
def S_dot_f(gamma, S_h, A, C, dC,N, step_size):
    S = np.zeros(N)
    S_dot=np.zeros(N)
    S=S_f(gamma, S_h, A, C, dC,N, step_size)
    for i in range(N):
        for j in range(N):
            S_dot[i] = S_dot[i] + S[i] *S[j]* (A[i][j] *Fij(C[i],C[j], gamma[i], gamma[j],  dC[i], dC[j])
            -A[j][i]*Fij(C[j],C[i], gamma[j], gamma[i],  dC[i], dC[j]))
    return S_dot





def S_dot_hist_f(S_h,N, step_size): #The historical rate of change of shares right before the boundary must be calculated.
    S_dot_hist=np.zeros(N)
    for i in range(N):
        S_dot_hist[i] = ((S_h[i][t_2]-S_h[i][t_1])/step_size + (S_h[i][t_1]-S_h[i][t_0])/step_size)/2 #is this correct?
    return S_dot_hist


#THIS IS WHERE EVERYTHING BECOMES ZERO
#Each element of the array this function returns is the derivative of a particular Sdot[i] with respect to the gamma value gamma[i].
def diff_S_dot_f(gamma, S_h, A, C, dC, N, step_size):
    S = np.zeros(N)
    diff_S_dot=np.zeros(N)
    S=S_f(gamma, S_h, A, C, dC,N, step_size)
    for i in range(N):
        for j in range(N):
            dFij = diff_Fij(C[i],C[j], gamma[i], gamma[j],  dC[i], dC[j])
            dFji = diff_Fij(C[j],C[i], gamma[j], gamma[i],  dC[j], dC[i])
            diff_S_dot[i] = diff_S_dot[i] + S[i]*S[j]* (A[i][j] *dFij
            -A[j][i]*dFji)
            
    return diff_S_dot






def L_f(gamma, step_size, S_h, A, C, dC, N):
    L=[]
    shar_dot = S_dot_f(gamma, S_h, A, C, dC,N, step_size)
    shar_dot_hist = S_dot_hist_f(S_h, N, step_size)
    L = (shar_dot[:] - shar_dot_hist[:])/step_size
    return L




def L_deriv_f(gamma, step_size, S_h, A, C, dC, N):
    L_deriv = diff_S_dot_f(gamma, S_h, A, C, dC, N, step_size)
    L_deriv = L_deriv/step_size
    return L_deriv



def newtonraphson(i, gamma, step_size, S_h, A, C, dC, N):
    f = L_f(gamma, step_size, S_h, A, C, dC, N)
    fprime = L_deriv_f(gamma, step_size, S_h, A, C, dC, N)
    if abs(f[i]/fprime[i])>100 or S_h[i,-1]==0:
        h=0
    else:
        h = f[i]/fprime[i]
    gamma[i]= gamma[i] - h
    return gamma



'''
Core Routine (uses all functions)
'''
#print(gamma)
iterations = 5

for b in range(20):
    for i in range(N):
        gamma=newtonraphson(i, gamma, step_size, S_h, A, C, dC, N)


print(gamma)

# S=S_f(gamma, S_h, A, C, dC,N)
#
# Shares['new'] = S
#
# S_h = Shares.iloc[:,-3:].values
#
# S=S_f(gamma, S_h, A, C, dC,N)
#
# Shares['new2'] = S
#
# Shares.to_excel("Shares.xlsx")



#space
