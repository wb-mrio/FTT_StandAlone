# -*- coding: utf-8 -*-
"""
Newton-Raphson example routine
"""
from sympy import *
from pylab import *

def f(x): #define a fnction
    y = x**3 - 3*x**2
    return y

def f_deriv(x): #approximates the derivative
    h=0.000001
    deriv = (f(x+h)-f(x))/h
    return deriv

def f_deriv_exact(x): #define the derivative exactly yourself
    y_prime = 3*x**2 - 6*x
    return y_prime

def newtonraphson(x): #the NR alogritm
    h = f(x)/f_deriv(x)
    return (x - h)

def iterate(x_0,n):
    x=x_0
    for i in range(n):
        x=newtonraphson(x)
    return x

print('The root of the equation is', iterate(3.5,4))

#The equation used as an example here has two roots, one at 0, and one at 3. If you start the iteration close to 3,
#you will see the algorithm will locate this root very quickly. If you start at 1.5, or even 1.7, the algorithm takes you
#to the zero root, showing why you need a close guess. If you start at 2, the algorithm will get lost and will provide an absurd number
#after only a few iterations. However, after a large number, e.g. 50, it will find the root at 3.

#Note that python will not return zero, and you will have found the root at zero if an very small number is returned instead.
