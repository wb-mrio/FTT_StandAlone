'''Code snippets which will be useful for gamma automation'''
# %%
# Third party imports
import numpy as np
from tqdm import tqdm

from SourceCode import model_class
# %%


def automation_init(model):
    scenario = 'S0'
    # model = model_class.ModelRun()
    modules = model.ftt_modules

    # Identifying the variables needed for automation
    share_variables = dict(zip(model.titles['Models_short'] , model.titles['Models_shares_var']))
    roc_variables = dict(zip(model.titles['Models_short'] ,model.titles['Models_shares_roc_var']))
    gamma_variables = dict(zip(model.titles['Models_short'] ,model.titles['Gamma_Value']))
    histend_vars = dict(zip(model.titles['Models_short'] , model.titles['Models_histend_var']))

 
    # Looping through all FTT modules
    for module in model.titles['Models_short']:
        if module in modules:
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
# %%
def automation_var_update(automation_variables, model):
    scenario = 'S0'

    modules = model.ftt_modules

    # Identifying the variables needed for automation
    share_variables = dict(zip(model.titles['Models_short'] , model.titles['Models_shares_var']))
    roc_variables = dict(zip(model.titles['Models_short'] ,model.titles['Models_shares_roc_var']))
    gamma_variables = dict(zip(model.titles['Models_short'] ,model.titles['Gamma_Value']))
    histend_vars = dict(zip(model.titles['Models_short'] , model.titles['Models_histend_var']))

    

    # Looping through all FTT modules
    for module in model.titles['Models_short']:
        if module in modules:
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
# %%
def roc_ratio(automation_variables):
    '''
    This function should calculate the average historical ROC and the simulated ROC for each module
    Then, it should calculate the ratio between them
    ratio = average_roc / average_hist_roc
    
    '''
    
    # Initialising variables
    automation_variables = automation_variables
    N = len(automation_variables)
    L = np.zeros(N)
    # get the histend variable
    histend_var = model.titles['Models_histend_var']
    # get year for that variable
    hist = model.histend[histend_var]

    

    for i in range(N):

        shar_dot_avg[i] = automation_variables[i][5:].sum(axis=1)/5
        shar_dot_hist[i] = automation_variables[i][0:5].sum(axis=1)/5

        if shar_dot_hist[i] == 0:
            L[i] = 0
        else:
            L[i] = shar_dot_avg[i]/shar_dot_hist[i]
    
        
    
    return L # do we want it to return the share_dot_avg and share_dot_hist as well?


    
# %%
def automation_algorithm(automation_variables):
    '''
    This function should contain the automation algorithm
    '''
    for iter in range(200):

    shares = automation_variables

    shar_dot = S_dot_f(gamma, shares, A, C, dC,N)

    shar_dot_hist = S_dot_hist_f(S_h, N)

    gradient_ratio = L_f(shar_dot, shar_dot_hist, N)

    # looping through technologies
    for i in range(N):
        # Check if gradient ratio is negative
        if gradient_ratio[i] < 0:
            # Check if historical average roc is negative
            if shar_dot_hist[i] < 0:
                # If yes, add to gamma value
                gamma[i] += 0.01
            # Check if historical average roc is positive
            if shar_dot_hist[i] > 0:
                # If yes, subtract from gamma value
                gamma[i] -= 0.01
        # Check if gradient ratio is positive
        if gradient_ratio[i] > 0:
            # Check if gradient ratio is very small
            if gradient_ratio[i] < 0.01:
                gamma[i] -= 0.01
            # Check if gradient ratio is very large
            if gradient_ratio[i] > 100:
                gamma[i] += 0.01
        # Check if gamma value is within bounds
        if gamma[i] > 1: gamma[i] = 1
        if gamma[i] < -1: gamma[i] = -1



    print(gamma)


    return automation_variables

# %%
def gamma_auto(model):
    # Initialising automation variables
    automation_variables = automation_init(model)

    # Iterative loop for gamma convergence goes here
    # Automation code goes here!!!!! (in loop)

    # Updating automation variables (in loop)
    automation_variables = automation_var_update(automation_variables,model)

    return automation_variables

# %%
model = model_class.ModelRun()
# %%
automation_variables = gamma_auto(model)

automation_variables
# $$
#    How to ensure gamma values are overwritten? Check Jamie's code
#    model.input["Gamma"][gamma_code][reg_pos,:,0,:] = np.array(gamma_values).reshape(-1,1)
    # model_folder = models.loc[ftt,"Short name"]

    # gamma_file = "{}_{}.csv".format(gamma_code,reg)
    # base_dir = "Inputs\\S0\\{}\\".format(model_folder)

    # gamma_df = pd.read_csv(os.path.join(rootdir,base_dir,gamma_file),index_col=0)
    # gamma_df.loc[:,:] = np.array(gamma_values).reshape(-1,1)

    # gamma_df.to_csv(os.path.join(rootdir,base_dir,gamma_file))

# %%
