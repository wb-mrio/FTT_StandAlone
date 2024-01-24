"""
Created on 18-10-2021

@author: RH

Exogenous electricity demand projections for FTT python
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy
import os
from pathlib import Path

import celib
# help(celib)

from celib import DB1, MRE, fillmat as fm
from numpy import nan



if __name__ == '__main__':

    # Define paths, directories and subfolders
    dirp = os.path.dirname(os.path.realpath(__file__))
    dirp_inputs = Path(dirp).parents[0]
    dirp_db = os.path.join(dirp, 'databank')
    dirp_mre = os.path.join(dirp, 'MREs')
    dirp_out_ftt = os.path.join(dirp_inputs, 'S0', 'FTT-P')
    dirp_out_gen = os.path.join(dirp_inputs, 'S0', 'General')



    # %% From databanks

    with DB1(os.path.join(dirp_db, 'U.db1')) as dbu:
        regions_short = dbu['RSHORTTI']
        fuel_users = dbu['FUTI']
        pop_groups = dbu["DPTI"]
        t2ti = dbu['T2TI']
        jti = dbu['JTI']
        erti = dbu['ERTI']


    with  DB1(os.path.join(dirp_db, 'F.db1')) as dbf:

        dbf_index = dbf.index
        FR08 = {}
        DPAR = {}
        RPOP = {}
        for region in regions_short:
            FR08[region] = pd.DataFrame(dbf['FR08_{}'.format(region)], index=fuel_users, columns=range(2003,2101))
            DPAR[region] = pd.DataFrame(dbf['DPAR_{}'.format(region)], index=pop_groups, columns=range(2003,2101))


    for region in regions_short:
        FR08[region].to_csv(os.path.join(dirp_out_gen, "FR08_{}.csv".format(region)))
        DPAR[region].to_csv(os.path.join(dirp_out_gen, "DPAR_{}.csv".format(region)))

    # %% From MRE

    with MRE(os.path.join(dirp_mre, 'Dan_ba.mre')) as mre:

        # MRE timeline:
        tl = np.arange(2010, 2060+1)

        # 3D variables
        mewlx = {}
        mercx = {}
        mewdx = {}
        metcx = {}
        mgamx = {}
        mewgx = {}
        mewkx = {}
        mewsx = {}
        mssmx = {}
        mlsmx = {}
        fretx = {}
        mcocx = {}
        mwicx = {}
        mwfcx = {}
        # Please add MWMC and MWMD to the DAN1.idiom file!
        mwmcx = {}
        mwmdx = {}

        # 2D variables
        msspx = pd.DataFrame(mre['MSSP'][0], index=regions_short, columns=tl)
        mlspx = pd.DataFrame(mre['MLSP'][0], index=regions_short, columns=tl)
        prsc = pd.DataFrame(mre['PRSC'][0], index=regions_short, columns=tl)
        ex = pd.DataFrame(mre['EX'][0], index=regions_short, columns=tl)

        for r, region in enumerate(regions_short):

            mewlx[region] = pd.DataFrame(mre['MEWL'][r], index=t2ti, columns=tl)
            mercx[region] = pd.DataFrame(mre['MERC'][r], index=erti, columns=tl)
            mewdx[region] = pd.DataFrame(mre['MEWD'][r], index=jti, columns=tl)
            metcx[region] = pd.DataFrame(mre['METC'][r], index=t2ti, columns=tl)
            mgamx[region] = pd.DataFrame(mre['MGAM'][r], index=t2ti, columns=tl)
            mewgx[region] = pd.DataFrame(mre['MEWG'][r], index=t2ti, columns=tl)
            mewkx[region] = pd.DataFrame(mre['MEWK'][r], index=t2ti, columns=tl)
            mewsx[region] = pd.DataFrame(mre['MEWS'][r], index=t2ti, columns=tl)
            mssmx[region] = pd.DataFrame(mre['MSSM'][r], index=t2ti, columns=tl)
            mlsmx[region] = pd.DataFrame(mre['MLSM'][r], index=t2ti, columns=tl)
            fretx[region] = pd.DataFrame(mre['FRET'][r], index=fuel_users, columns=tl)
            mcocx[region] = pd.DataFrame(mre['MCOC'][r], index=t2ti, columns=tl)
            mwicx[region] = pd.DataFrame(mre['MWIC'][r], index=t2ti, columns=tl)
            mwfcx[region] = pd.DataFrame(mre['MWFC'][r], index=t2ti, columns=tl)
            mwmcx[region] = pd.DataFrame(mre['MWMC'][r], index=t2ti, columns=tl)
            mwmdx[region] = pd.DataFrame(mre['MWMD'][r], index=t2ti, columns=tl)



    msspx.to_csv(os.path.join(dirp_out_ftt, "MSSPX.csv"))
    mlspx.to_csv(os.path.join(dirp_out_ftt, "MLSPX.csv"))
    prsc.to_csv(os.path.join(dirp_out_ftt, "PRSCX.csv"))
    ex.to_csv(os.path.join(dirp_out_ftt, "EXX.csv"))

    for region in regions_short:

        mewlx[region].to_csv(os.path.join(dirp_out_ftt, "MEWLX_{}.csv".format(region)))
        mercx[region].to_csv(os.path.join(dirp_out_ftt, "MERCX_{}.csv".format(region)))
        mewdx[region].to_csv(os.path.join(dirp_out_ftt, "MEWDX_{}.csv".format(region)))
        metcx[region].to_csv(os.path.join(dirp_out_ftt, "METCX_{}.csv".format(region)))
        mgamx[region].to_csv(os.path.join(dirp_out_ftt, "MGAMX_{}.csv".format(region)))
        mgamx[region].to_csv(os.path.join(dirp_out_ftt, "MGAM_{}.csv".format(region)))
        mewgx[region].to_csv(os.path.join(dirp_out_ftt, "MEWGX_{}.csv".format(region)))
        mewkx[region].to_csv(os.path.join(dirp_out_ftt, "MEWKX_{}.csv".format(region)))
        mewsx[region].to_csv(os.path.join(dirp_out_ftt, "MEWSX_{}.csv".format(region)))
        mssmx[region].to_csv(os.path.join(dirp_out_ftt, "MSSMX_{}.csv".format(region)))
        mlsmx[region].to_csv(os.path.join(dirp_out_ftt, "MLSMX_{}.csv".format(region)))
        fretx[region].to_csv(os.path.join(dirp_out_ftt, "FRETX_{}.csv".format(region)))
        mcocx[region].to_csv(os.path.join(dirp_out_ftt, "MCOCX_{}.csv".format(region)))
        mwicx[region].to_csv(os.path.join(dirp_out_ftt, "MWICX_{}.csv".format(region)))
        mwfcx[region].to_csv(os.path.join(dirp_out_ftt, "MWFCX_{}.csv".format(region)))
        mwmcx[region].to_csv(os.path.join(dirp_out_ftt, "MWMCX_{}.csv".format(region)))
        mwmdx[region].to_csv(os.path.join(dirp_out_ftt, "MWMDX_{}.csv".format(region)))











#space
