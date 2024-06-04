'''Code snippets which will be useful for gamma automation'''
# %%
# Third party imports
import numpy as np
from tqdm import tqdm

from SourceCode import model_class



def automation_init(model):
    scenario = 'S0'
    # %%
    # model = model_class.ModelRun()
    modules = model.ftt_modules
    # %%
    # Identifying the variables needed for automation
    share_variables = dict(zip(model.titles['Models'] , model.titles['Models_shares_var']))
    roc_variables = dict(zip(model.titles['Models'] ,model.titles['Models_shares_roc_var']))
    gamma_variables = dict(zip(model.titles['Models'] ,model.titles['Gamma_Value']))
    histend_vars = dict(zip(model.titles['Models'] , model.titles['Models_histend_var']))

    # %%
    # Looping through all FTT modules
    for module in modules:
        # Automation variable list for this module
        automation_var_list = [share_variables[module],roc_variables[module],gamma_variables[module]]
        # Establisting timeline for automation algorithm
        model.timeline = np.arange(model.histend[histend_vars[module]]-5, model.histend[histend_vars[module]]+5)
        years = list(model.timeline)
        years = [int(x) for x in years]

    # Initialising container for automation variables
        automation_variables = {module: {var: np.full_like(model.input[scenario][var][:,:,:,:len(model.timeline)], 0) for var in automation_var_list}}
        # Looping through years in automation timeline
        for year_index, year in enumerate(model.timeline):

            # Solving the model for each year
            model.variables, model.lags = model.solve_year(year,year_index,scenario)

            # Populate variable container for automation
            for var in automation_var_list:
                if 'TIME' in model.dims[var]:
                    automation_variables[module][var][:, :, :, year_index] = model.variables[var]
                else:
                    automation_variables[module][var][:, :, :, 0] = model.variables[var]

    return automation_variables

def automation_var_update(automation_variables, model):
    scenario = 'S0'
    # %%
    modules = model.ftt_modules
    # %%
    # Identifying the variables needed for automation
    share_variables = dict(zip(model.titles['Models'] , model.titles['Models_shares_var']))
    roc_variables = dict(zip(model.titles['Models'] ,model.titles['Models_shares_roc_var']))
    gamma_variables = dict(zip(model.titles['Models'] ,model.titles['Models_Gamma_Value']))
    histend_vars = dict(zip(model.titles['Models'] , model.titles['Models_histend_var']))

    
    # %%
    # Looping through all FTT modules
    for module in modules:
        # Automation variable list for this module
        automation_var_list = [share_variables[module],roc_variables[module],gamma_variables[module]]
        # Establisting timeline for automation algorithm
        model.timeline = np.arange(model.histend[histend_vars[module]]-5, model.histend[histend_vars[module]]+5)
        years = list(model.timeline)
        years = [int(x) for x in years]

        # Overwriting input data for gamma values (broadcast to all years)
        model.input[scenario][gamma_variables[module]][:,:,0,:] = automation_variables[module][gamma_variables[module]][:, :, :, 0]

        # Looping through years in automation timeline
        for year_index, year in enumerate(model.timeline):

            # Solving the model for each year
            model.variables, model.lags = model.solve_year(year,year_index,scenario)

            # Populate variable container for automation
            for var in automation_var_list:
                if 'TIME' in model.dims[var]:
                    automation_variables[module][var][:, :, :, year_index] = model.variables[var]
                else:
                    automation_variables[module][var][:, :, :, 0] = model.variables[var]

    return automation_variables

def gamma_auto(model):
    automation_variables = automation_init(model)

    automation_variables = automation_var_update(automation_variables,model)

    return automation_variables

# %%
model = model_class.ModelRun()

automation_variables = gamma_auto(model)

automation_variables

#    How to ensure gamma values are overwritten? Check Jamie's code
#    model.input["Gamma"][gamma_code][reg_pos,:,0,:] = np.array(gamma_values).reshape(-1,1)
    # model_folder = models.loc[ftt,"Short name"]

    # gamma_file = "{}_{}.csv".format(gamma_code,reg)
    # base_dir = "Inputs\\S0\\{}\\".format(model_folder)

    # gamma_df = pd.read_csv(os.path.join(rootdir,base_dir,gamma_file),index_col=0)
    # gamma_df.loc[:,:] = np.array(gamma_values).reshape(-1,1)

    # gamma_df.to_csv(os.path.join(rootdir,base_dir,gamma_file))

# %%
