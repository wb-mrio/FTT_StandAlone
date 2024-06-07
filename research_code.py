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
def roc_ratio(automation_variables, model):
    '''
    This function should calculate the average historical ROC and the simulated ROC for each module
    Then, it should calculate the ratio between them
    ratio = average_roc / average_hist_roc
    
    '''
    scenario = 'S0'
    
    # Initialising variables
    modules = model.ftt_modules
    regions = len(model.titles['RTI_short'])


    # Identifying the variables needed for automation
    share_variables = dict(zip(model.titles['Models_short'] , model.titles['Models_shares_var']))
    roc_variables = dict(zip(model.titles['Models_short'] ,model.titles['Models_shares_roc_var']))
    gamma_variables = dict(zip(model.titles['Models_short'] ,model.titles['Gamma_Value']))
    histend_vars = dict(zip(model.titles['Models_short'] , model.titles['Models_histend_var']))
    techs_vars = dict(zip(model.titles['Models_short'] , model.titles['tech_var']))


    # Looping through all FTT modules
    for module in model.titles['Models_short']:
        if module in modules:
            # Get variable for tech list
            tech_var = techs_vars[module]
            # Get number of technologies
            N_techs = len(model.titles[tech_var])

            # Initialize containers for rates of change
            roc_gradient = np.zeros([regions, N_techs])  # container for ratio of average roc to average hist roc for all regions
            hist_share_avg = np.zeros((regions, N_techs))  # container for average roc for all regions
            sim_share_avg = np.zeros((regions, N_techs))  # container for average hist roc for all regions
        

            for reg in range(regions):
                # Temporary line for dealing with Nans
                #automation_variables['FTT-P']['MSRC'] = np.nan_to_num(automation_variables['FTT-P']['MSRC'])
                            
                # Loop through technologies
                for i in range(N_techs):
                    # seems to be an extra dimension in there set at 0 
                    sim_share_avg[reg][i] = automation_variables[module][roc_variables[module]][reg][i][0][4:].sum()/4  
                    
                    hist_share_avg[reg][i] = automation_variables[module][roc_variables[module]][reg][i][0][0:4].sum()/4

                    if hist_share_avg[reg][i] == 0:
                        roc_gradient[reg][i] = 0
                    else:
                        roc_gradient[reg][i] = sim_share_avg[reg][i]/hist_share_avg[reg][i]

            automation_variables[module]['roc_gradient'] = roc_gradient
            automation_variables[module]['hist_share_avg'] = hist_share_avg

            # Temporary line for dealing with Nans
            #automation_variables['FTT-P']['MSRC'] = np.nan_to_num(automation_variables['FTT-P']['MSRC'])
                        
        
    
    return automation_variables # do we want it to return the share_dot_avg as well?

    #### Different names for share vars
    
# %%
def automation_algorithm(automation_variables, model):
    '''
    This function should contain the automation algorithm
    '''

            # Get number of technologies
            N_techs = len(model.titles[techs_vars[module]])

            for reg in range(regions):
                # Temporary line for dealing with Nans
                #automation_variables['FTT-P']['MSRC'] = np.nan_to_num(automation_variables['FTT-P']['MSRC'])
                
                # take first column of gammas, will be broadcast later
                # this can be either side of the tech loop, not sure which is best  
                gamma = automation_variables[module][gamma_variables[module]][reg, :, 0, 0] # taking just first col of gammas
                automation_variables[module][gamma_variables[module]+'_LAG'][reg, :, 0, 0] = gamma

                # Loop through technologies
                for i in range(N_techs):
                    
                    # Get gradient between hsitorical and simulated ROC
                    gradient_ratio = automation_variables[module]['roc_gradient'][reg, i]
                    hist_share_avg = automation_variables[module]['hist_share_avg'][reg, i]

                    # Check if gradient ratio is negative
                    if gradient_ratio < 0:
                        # Check if historical average roc is negative
                        if hist_share_avg < 0:
                            # If yes, add to gamma value
                            gamma[i] += 0.01
                        # Check if historical average roc is positive
                        if hist_share_avg > 0:
                            # If yes, subtract from gamma value
                            gamma[i] -= 0.01
                    # Check if gradient ratio is positive
                    if gradient_ratio > 0:
                        # Check if gradient ratio is very small
                        if gradient_ratio < 0.5:
                            # Historical gradient is steeper than simulated gradient
                            # If steep and negative, add to gamma value
                            if hist_share_avg < 0:
                                gamma[i] += 0.01
                            # If steep and positive, subtract from gamma value
                            if hist_share_avg > 0:
                                gamma[i] -= 0.01
                        # Check if gradient ratio is very large
                        if gradient_ratio > 2:
                            # Simulated gradient is steeper than historical gradient
                            # If steep and negative, subtract from gamma value
                            if hist_share_avg < 0:
                                gamma[i] -= 0.01
                            # If steep and positive, add to gamma value
                            if hist_share_avg > 0:
                                gamma[i] += 0.01
                    # Check if gamma value is within bounds
                    if gamma[i] > 1: gamma[i] = 1 
                    if gamma[i] < -1: gamma[i] = -1


                gamma = np.tile(gamma.reshape(-1, 1), (1, 8)).reshape(24, 1, 8) # reshape format for whole period

                automation_variables[module][gamma_variables[module]][reg, :, :, :] = copy.deepcopy(gamma)
                print('Gamma values updated for region', model.titles['RTI'][reg])

    return automation_variables

# %%
def gamma_auto(model):
    # Initialising variables
    scenario = 'S0'
    
    # Initialising variables
    modules = model.ftt_modules
    regions = len(model.titles['RTI_short'])


    # Identifying the variables needed for automation
    share_variables = dict(zip(model.titles['Models_short'] , model.titles['Models_shares_var']))
    roc_variables = dict(zip(model.titles['Models_short'] ,model.titles['Models_shares_roc_var']))
    gamma_variables = dict(zip(model.titles['Models_short'] ,model.titles['Gamma_Value']))
    histend_vars = dict(zip(model.titles['Models_short'] , model.titles['Models_histend_var']))
    techs_vars = dict(zip(model.titles['Models_short'] , model.titles['tech_var']))

    for module in model.titles['Models_short']:
        if module in modules:
    # Initialising automation variables
    automation_variables = automation_init(model)

    # Iterative loop for gamma convergence goes here
    for iter in tqdm(range(10)):

        # have region and module loop here

        # Calculate ROC ratio
        automation_variables = roc_ratio(automation_variables, model)
        
        # Perform automation algorithm
        automation_variables = automation_algorithm(automation_variables, model)

        # Check for convergence in region and module loop
        if all(np.absolute(gamma - gamma_lag)) < 0.01:
            break

        # Updating automation variables
        automation_variables = automation_var_update(automation_variables,model)
        print('Gamma automation iteration:', iter, 'completed')

    return automation_variables

##%

def gamma_save(automation_variables, model):


    # $$
#    How to ensure gamma values are overwritten? Check Jamie's code
#    model.input["Gamma"][gamma_code][reg_pos,:,0,:] = np.array(gamma_values).reshape(-1,1)
    # model_folder = models.loc[ftt,"Short name"]

    # gamma_file = "{}_{}.csv".format(gamma_code,reg)
    # base_dir = "Inputs\\S0\\{}\\".format(model_folder)

    # gamma_df = pd.read_csv(os.path.join(rootdir,base_dir,gamma_file),index_col=0)
    # gamma_df.loc[:,:] = np.array(gamma_values).reshape(-1,1)

    # gamma_df.to_csv(os.path.join(rootdir,base_dir,gamma_file))

# %% ###################   START OF MAIN CODE RUN



model = model_class.ModelRun()






# %% Run combined function
automation_variables = gamma_auto(model)

#%%
automation_variables = automation_init(model)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%
automation_variables = roc_ratio(automation_variables, model)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%

automation_variables = automation_algorithm(automation_variables, model)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%

automation_variables = automation_var_update(automation_variables, model)
print(automation_variables['FTT-P']['MGAM'][0, :, 0, :])

#%%








#%%
reg = 0 # this will be provided by the loop
automation_variables = automation_algorithm(automation_variables, L, shar_dot_hist, reg)





