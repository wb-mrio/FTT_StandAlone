'''Code snippets which will be useful for gamma automation'''
# %%
# Third party imports
import numpy as np
from tqdm import tqdm
import copy

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
            model.timeline = np.arange(model.histend[histend_vars[module]]-4, model.histend[histend_vars[module]]+4) 
            years = list(model.timeline)
            years = [int(x) for x in years] ## do we need these? they are not used

        # Initialising container for automation variables
            automation_variables = {module: {var: np.full_like(model.input[scenario][var][:,:,:,:len(model.timeline)], 0) for var in automation_var_list}}
            # Looping through years in automation timeline
            for year_index, year in enumerate(model.timeline):

                # Solving the model for each year
                model.variables, model.lags = model.solve_year(year,year_index,scenario)
                # the year_index starts at 2013 = 0, is this right given we start earlier?
                # Nans are introduced here

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
            model.timeline = np.arange(model.histend[histend_vars[module]]-4, model.histend[histend_vars[module]]+4)
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
def roc_ratio(automation_variables, model, reg):
    '''
    This function should calculate the average historical ROC and the simulated ROC for each module
    Then, it should calculate the ratio between them
    ratio = average_roc / average_hist_roc
    
    '''
    
    # Initialising variables
    titles = model.titles
    automation_variables = automation_variables
    regions = len(model.titles['RTI_short'])
    N = len(model.titles['T2TI']) # no. techs

    ## Initiailising containers
    shar_dot_avg = np.zeros(len(model.titles['T2TI'])) # container for average roc
    shar_dot_hist = np.zeros(len(model.titles['T2TI'])) # container for average hist roc
    L = np.zeros([len(titles['RTI']), len(titles['T2TI'])]) # container for ratio of average roc to average hist roc

    # Temporary line for dealing with Nans
    automation_variables['FTT-P']['MSRC'] = np.nan_to_num(automation_variables['FTT-P']['MSRC'])
    
    # Loop through regions
    
    # Loop through technologies
    for i in range(N):
        # seems to be an extra dimension in there set at 0 
        shar_dot_avg[i] = automation_variables['FTT-P']['MSRC'][reg][i][0][5:].sum()/5  
        
        shar_dot_hist[i] = automation_variables['FTT-P']['MSRC'][reg][i][0][0:5].sum()/5

        if shar_dot_hist[i] == 0:
            L[reg][i] = 0
        else:
            L[reg][i] = shar_dot_avg[i]/shar_dot_hist[i]
    
        
    
    return L, shar_dot_avg, shar_dot_hist # do we want it to return the share_dot_avg as well?

    #### Different names for share vars
    
# %%
def automation_algorithm(automation_variables, L, shar_dot_hist, reg):
    '''
    This function should contain the automation algorithm
    '''
    #for iter in range(200): activate later

    gamma = automation_variables['FTT-P']['MGAM'][reg, :, 0, 0] # taking just first col of gammas
    # ok I completely forgot that if you don't do deep copy it automatically updates the original variable
    # this has cost me a depressingly long time

    N = len(model.titles['T2TI']) # no. techs, do we need model within this function to get these?

    gradient_ratio = L[reg]

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
        if gamma[i] > 1: gamma[i] = 1 # this just picks the first value in the gammas, they're the same but this seems wrong
        if gamma[i] < -1: gamma[i] = -1

    gamma = np.tile(gamma.reshape(-1, 1), (1, 10)).reshape(24, 1, 10) # reshape format for whole period

    automation_variables['FTT-P']['MGAM'][reg, :, :, :] = copy.deepcopy(gamma)
    

    return automation_variables

# %%
def gamma_auto(model):
    # Initialising automation variables
    automation_variables = automation_init(model)

    # Iterative loop for gamma convergence goes here
    for iter in tqdm(range(3)):
        if iter == 0:
            print('stop')
            
        #shares = S_f(gamma, S_h, A, C, dC,N) thow does this line come in?
        # automation_var_update??

        for reg in range(len(model.titles['RTI_short'])):

            # Determine roc, outputs 71 x 24 matrix
            L, shar_dot_avg, shar_dot_hist = roc_ratio(automation_variables, model, reg)

            # Automation code goes here!!!!! (in loop)
            automation_variables = automation_algorithm(automation_variables, L, shar_dot_hist, reg)

            print('region', reg, 'done')

        # Updating automation variables (in loop)
        automation_variables = automation_var_update(automation_variables,model)
        print('iteration', iter, 'done')

    return automation_variables



# %%
model = model_class.ModelRun()


# %%
automation_variables = gamma_auto(model)

#%%
automation_variables = automation_init(model)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%
L, shar_dot_avg, shar_dot_hist = roc_ratio(automation_variables, model)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%
reg = 0
automation_variables = automation_algorithm(automation_variables, L, shar_dot_hist, reg)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%

automation_variables = automation_var_update(automation_variables, model)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%








#%%
reg = 0 # this will be provided by the loop
automation_variables = automation_algorithm(automation_variables, L, shar_dot_hist, reg)


# $$
#    How to ensure gamma values are overwritten? Check Jamie's code
#    model.input["Gamma"][gamma_code][reg_pos,:,0,:] = np.array(gamma_values).reshape(-1,1)
    # model_folder = models.loc[ftt,"Short name"]

    # gamma_file = "{}_{}.csv".format(gamma_code,reg)
    # base_dir = "Inputs\\S0\\{}\\".format(model_folder)

    # gamma_df = pd.read_csv(os.path.join(rootdir,base_dir,gamma_file),index_col=0)
    # gamma_df.loc[:,:] = np.array(gamma_values).reshape(-1,1)

    # gamma_df.to_csv(os.path.join(rootdir,base_dir,gamma_file))


