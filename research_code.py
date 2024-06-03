'''Code snippets which will be useful for gamma automation'''
# Third party imports
import numpy as np
from tqdm import tqdm

# Local library imports
# Separate FTT modules

from SourceCode import model_class

scenario = 'S0'
# %%
model = model_class.ModelRun()
# %%
model.timeline = np.arange(model.histend['MEWG']-5, model.histend['MEWG']+5)
years = list(model.timeline)
years = [int(x) for x in years]
model.output = {scenario: {var: np.full_like(model.input[scenario][var][:,:,:,:10], 0) for var in model.input[scenario]}}
for year_index, year in enumerate(model.timeline):
                model.variables, model.lags = model.solve_year(year,year_index,scenario)

                # Populate output container
                for var in model.variables:
                    if 'TIME' in model.dims[var]:
                        model.output[scenario][var][:, :, :, year_index] = model.variables[var]
                    else:
                        model.output[scenario][var][:, :, :, 0] = model.variables[var]

shares = model.output['S0']['MEWS']

shares