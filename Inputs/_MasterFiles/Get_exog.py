"""
Created on 18-10-2021

@author: RH

Exogenous variables for the standalone version. 

This includes exogenous price and electricity demand. 
You can also convert variables for model intercomparison. 
"""

import numpy as np
import pandas as pd
import copy
import os
from pathlib import Path

import celib
# help(celib)

from celib import DB1, MRE, fillmat as fm



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
            
            
    # with  DB1(os.path.join(dirp_db, 'E.db1')) as dbe:
    #     dbe_index = dbe.index
    #     PFRO = {}
    #     PFRG = {}
    #     PFRM = {}
    #     PFRE = {}
    #     PFRC = {}
    #     PFRB = {}

    #     for region in regions_short:

    #         PFRO[region] = pd.DataFrame(dbf['PFRO_{}'.format(region)], index=fuel_users, columns=range(2003,2101))
    #         PFRG[region] = pd.DataFrame(dbf['PFRG_{}'.format(region)], index=fuel_users, columns=range(2003,2101))
    #         PFRM[region] = pd.DataFrame(dbf['PFRM_{}'.format(region)], index=fuel_users, columns=range(2003,2101))
    #         PFRE[region] = pd.DataFrame(dbf['PFRE_{}'.format(region)], index=fuel_users, columns=range(2003,2101))
    #         PFRC[region] = pd.DataFrame(dbf['PFRC_{}'.format(region)], index=fuel_users, columns=range(2003,2101))
    #         PFRB[region] = pd.DataFrame(dbf['PFRB_{}'.format(region)], index=fuel_users, columns=range(2003,2101))


    # for region in regions_short:
    #     FR08[region].to_csv(os.path.join(dirp_out_gen, "FR08_{}.csv".format(region)))
    #     DPAR[region].to_csv(os.path.join(dirp_out_gen, "DPAR_{}.csv".format(region)))
    #     PFRB[region].to_csv(os.path.join(dirp_out_gen, "PFRB_{}.csv".format(region)))
    #     PFRC[region].to_csv(os.path.join(dirp_out_gen, "PFRC_{}.csv".format(region)))
    #     PFRO[region].to_csv(os.path.join(dirp_out_gen, "PFRO_{}.csv".format(region)))
    #     PFRM[region].to_csv(os.path.join(dirp_out_gen, "PFRM_{}.csv".format(region)))
    #     PFRE[region].to_csv(os.path.join(dirp_out_gen, "PFRE_{}.csv".format(region)))
    #     PFRG[region].to_csv(os.path.join(dirp_out_gen, "PFRG_{}.csv".format(region)))

    # %% From MRE

    with MRE(os.path.join(dirp_mre, 'DAN1.mre')) as mre:

        # MRE timeline:
        tl = np.arange(2010, 2070+1)
        
        mre_out = copy.deepcopy(mre)

        # # 3D variables
        mewlx = {}
        # mercx = {}
        mewdx = {}
        metcx = {}
        # mgamx = {}
        mewgx = {}
        mewkx = {}
        mewsx = {}
        # mssmx = {}
        mlsmx = {}
        fretx = {}
        mcocx = {}
        # mwicx = {}
        mwfcx = {}
        msspx = {}
        mlspx = {}
        # mwkax = {}
        # pfrb = {}
        # pfrc = {}
        # pfrm = {}
        # pfre = {}
        # pfro = {}
        # pfrg = {}
        # # Please add MWMC and MWMD to the DAN1.idiom file!
        mwmcx = {}
        mmcdx = {}
        mes2x = {}
        repp = {}
        fets = {}
        
        # mtcdx = {}
        
        mcfcx = {}

        # # 2D variables
        prsc = pd.DataFrame(mre['PRSC'][0], index=regions_short, columns=tl)
        ex = pd.DataFrame(mre['EX'][0], index=regions_short, columns=tl)
        rex = pd.DataFrame(mre['REX'][0], index=regions_short, columns=tl)

        repp = pd.DataFrame(mre["REPP"][0], index=regions_short, columns=tl)

        for r, region in enumerate(regions_short):

            mewlx[region] = pd.DataFrame(mre['MEWL'][r], index=t2ti, columns=tl)
            # mercx[region] = pd.DataFrame(mre['MERC'][r], index=erti, columns=tl)
            mewdx[region] = pd.DataFrame(mre['MEWD'][r], index=jti, columns=tl)
            metcx[region] = pd.DataFrame(mre['METC'][r], index=t2ti, columns=tl)
            # mtcdx[region] = pd.DataFrame(mre['MTCD'][r], index=t2ti, columns=tl)
            # mgamx[region] = pd.DataFrame(mre['MGAM'][r], index=t2ti, columns=tl)
            mewgx[region] = pd.DataFrame(mre['MEWG'][r], index=t2ti, columns=tl)
            mewkx[region] = pd.DataFrame(mre['MEWK'][r], index=t2ti, columns=tl)
            mewsx[region] = pd.DataFrame(mre['MEWS'][r], index=t2ti, columns=tl)
            # mssmx[region] = pd.DataFrame(mre['MSSM'][r], index=t2ti, columns=tl)
            mlsmx[region] = pd.DataFrame(mre['MLSM'][r], index=t2ti, columns=tl)
            fretx[region] = pd.DataFrame(mre['FRET'][r], index=fuel_users, columns=tl)
            mcocx[region] = pd.DataFrame(mre['MCOC'][r], index=t2ti, columns=tl)
            # mwicx[region] = pd.DataFrame(mre['MWIC'][r], index=t2ti, columns=tl)
            mwfcx[region] = pd.DataFrame(mre['MWFC'][r], index=t2ti, columns=tl)
            mwmcx[region] = pd.DataFrame(mre['MWMC'][r], index=t2ti, columns=tl)
            #mmcdx[region] = pd.DataFrame(mre['MMCD'][r], index=t2ti, columns=tl)
            #msspx[region] = pd.DataFrame(mre['MSSP'][r], index=t2ti, columns=tl)
            mlspx[region] = pd.DataFrame(mre['MLSP'][r], index=t2ti, columns=tl)
            # mwkax[region] = pd.DataFrame(mre['MWKA'][r], index=t2ti, columns=tl)
            mcfcx[region] = pd.DataFrame(mre['MCFC'][r], index=t2ti, columns=tl)
            mes2x[region] = pd.DataFrame(mre['MES2'][r], index=t2ti, columns=tl)
            # pfrb[region] = pd.DataFrame(mre["PFRB"][r], index=fuel_users, columns=tl)
            # pfrc[region] = pd.DataFrame(mre["PFRC"][r], index=fuel_users, columns=tl)
            # pfro[region] = pd.DataFrame(mre["PFRO"][r], index=fuel_users, columns=tl)
            # pfrm[region] = pd.DataFrame(mre["PFRM"][r], index=fuel_users, columns=tl)
            # pfre[region] = pd.DataFrame(mre["PFRE"][r], index=fuel_users, columns=tl)
            # pfrg[region] = pd.DataFrame(mre["PFRG"][r], index=fuel_users, columns=tl)

    
    # Exogenous inputs    
    prsc.to_csv(os.path.join(dirp_out_ftt, "PRSCX.csv"))
    ex.to_csv(os.path.join(dirp_out_ftt, "EXX.csv"))
    rex.to_csv(os.path.join(dirp_out_ftt, "REXX.csv"))
    repp.to_csv(os.path.join(dirp_out_ftt, "REPPX.csv"))


    for region in regions_short:
        pass
    
        # Exogenous inputs
        mewdx[region].to_csv(os.path.join(dirp_out_ftt, "MEWDX_{}.csv".format(region)))
        mcfcx[region].to_csv(os.path.join(dirp_out_ftt, "MCFCX_{}.csv".format(region)))
        

        # pfrb[region].to_csv(os.path.join(dirp_out_gen, "PFRB_{}.csv".format(region)))
        # pfrc[region].to_csv(os.path.join(dirp_out_gen, "PFRC_{}.csv".format(region)))
        # pfrm[region].to_csv(os.path.join(dirp_out_gen, "PFRM_{}.csv".format(region)))
        # pfro[region].to_csv(os.path.join(dirp_out_gen, "PFRO_{}.csv".format(region)))
        # pfre[region].to_csv(os.path.join(dirp_out_gen, "PFRE_{}.csv".format(region)))
        # pfrg[region].to_csv(os.path.join(dirp_out_gen, "PFRG_{}.csv".format(region)))


        # Only there for debugging
        mewlx[region].to_csv(os.path.join(dirp_out_ftt, "MEWLX_{}.csv".format(region)))
        # mercx[region].to_csv(os.path.join(dirp_out_ftt, "MERCX_{}.csv".format(region)))
        metcx[region].to_csv(os.path.join(dirp_out_ftt, "METCX_{}.csv".format(region)))
        # mtcdx[region].to_csv(os.path.join(dirp_out_ftt, "MTCDX_{}.csv".format(region)))
        # mgamx[region].to_csv(os.path.join(dirp_out_ftt, "MGAMX_{}.csv".format(region)))
        # mgamx[region].to_csv(os.path.join(dirp_out_ftt, "MGAM_{}.csv".format(region)))
        #mewgx[region].to_csv(os.path.join(dirp_out_ftt, "MEWGX_{}.csv".format(region)))
        #mewkx[region].to_csv(os.path.join(dirp_out_ftt, "MEWKX_{}.csv".format(region)))
        #mewsx[region].to_csv(os.path.join(dirp_out_ftt, "MEWSX_{}.csv".format(region)))
        # mssmx[region].to_csv(os.path.join(dirp_out_ftt, "MSSMX_{}.csv".format(region)))
        mlsmx[region].to_csv(os.path.join(dirp_out_ftt, "MLSMX_{}.csv".format(region)))
        #mcocx[region].to_csv(os.path.join(dirp_out_ftt, "MCOCX_{}.csv".format(region)))
        # mwicx[region].to_csv(os.path.join(dirp_out_ftt, "MWICX_{}.csv".format(region)))
        #mwfcx[region].to_csv(os.path.join(dirp_out_ftt, "MWFCX_{}.csv".format(region)))
        #mwmcx[region].to_csv(os.path.join(dirp_out_ftt, "MWMCX_{}.csv".format(region)))
        #mmcdx[region].to_csv(os.path.join(dirp_out_ftt, "MMCDX_{}.csv".format(region)))
        #msspx[region].to_csv(os.path.join(dirp_out_ftt, "MSSPX_{}.csv".format(region)))
        mlspx[region].to_csv(os.path.join(dirp_out_ftt, "MLSPX_{}.csv".format(region)))
        # mwkax[region].to_csv(os.path.join(dirp_out_ftt, "MWKA_{}.csv".format(region)))
        #mes2x[region].to_csv(os.path.join(dirp_out_ftt, "MES2X_{}.csv".format(region)))
        
        # Not sure
        #fretx[region].to_csv(os.path.join(dirp_out_ftt, "FRETX_{}.csv".format(region)))
