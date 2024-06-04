'''Code snippets which will be useful for gamma automation'''
# %%
# Third party imports
import numpy as np
from tqdm import tqdm

from SourceCode import model_class

scenario = 'S0'
# %%
model = model_class.ModelRun()
modules = model.ftt_modules
# %%
# Identifying the variables needed for automation
automation_var_list = model.titles['Models_shares_var'] + model.titles['Models_shares_roc_var'] + model.titles['Models_gamma_var']
share_variables = dict(zip(model.titles['Models'] , model.titles['Models_shares_var']))
roc_variables = dict(zip(model.titles['Models'] ,model.titles['Models_shares_roc_var']))
gamma_variables = dict(zip(model.titles['Models'] ,model.titles['Models_gamma_var']))
histend_vars = dict(zip(model.titles['Models'] , model.titles['Models_histend_var']))
# %%
# Looping through all FTT modules
for module in modules:

    # Establisting timeline for automation algorithm
    model.timeline = np.arange(model.histend[histend_vars[module]]-5, model.histend[histend_vars[module]]+5)
    years = list(model.timeline)
    years = [int(x) for x in years]

    # Initialising container for automation variables
    automation_varibales = {var: np.full_like(model.input[scenario][var][:,:,:,:len(model.timeline)], 0) for var in automation_var_list}

    # Looping through years in automation timeline
    for year_index, year in enumerate(model.timeline):

        # Solving the model for each year
        model.variables, model.lags = model.solve_year(year,year_index,scenario)

        # Populate variable container for automation
        for var in automation_var_list:
            if 'TIME' in model.dims[var]:
                automation_varibales[var][:, :, :, year_index] = model.variables[var]
            else:
                automation_varibales[var][:, :, :, 0] = model.variables[var]

   

