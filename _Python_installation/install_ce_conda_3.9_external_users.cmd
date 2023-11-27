@rem install_ce_conda-packages.cmd
@rem =============================
@rem Windows Command Script to install the recommended packages and versions
@rem for a Python installation at CE.

@rem conda packages
call conda install -c defaults -n base paste=3.5.0 coverage=6.3.2 xlwt=1.3.0 

call conda install -c conda-forge -n base dash=2.8.1 bottle=0.12.23 einops=0.6.0 pipdeptree=2.5.0
