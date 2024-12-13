# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 17:13:22 2024

This script produces one figure. That is, the bare levelised cost difference,
based on the policy. 

@author: Femke Nijsse
"""

# Import the results pickle file
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as ticker


from preprocessing import get_output, get_metadata, save_fig, save_data

import config

#%%
output_file = "Results_sxp.pickle"
titles, fig_dir, tech_titles, models, shares_vars = get_metadata()


price_names = {"FTT:P": "MECW battery only", "FTT:Tr": "TEWC", "FTT:H": "HEWC", "FTT:Fr": "ZTLC"}
tech_variable = {"FTT:P": 18, "FTT:Tr": 19, "FTT:H": 10, "FTT:Fr": 13}
operation_cost_name = {"FTT:P": "MLCO"}

tech_name = {"FTT:P": "Solar PV", "FTT:Tr": "EV (mid-range)",
             "FTT:H": "Air-air heat pump", "FTT:Fr": "Small electric truck"}

year_inds = [year - 2010 for year in [2024, 2035, 2050]]

# Define the percentage difference function
def get_percentage_difference(clean_price, dirty_price):
    return 100 * (clean_price - dirty_price) / dirty_price


def get_weighted_costs(output, model, tech_variable, year_inds):
    """Get the weighted cost based on the scenario (output), model,
    tech_variable and the indices of the years of interest.
    """
    
    if model == "FTT:P" and tech_variable in [2, 6]:
        prices = output[operation_cost_name[model]][:, tech_variable, 0, year_inds]
    else:
        prices = output[price_names[model]][:, tech_variable, 0, year_inds]
    
    # Weigh by total size of the market per region
    weights = np.sum(output[shares_vars[model]][:, :, 0, year_inds], axis=1)    
    weighted_prices = np.average(prices, weights=weights, axis=0)

    
    return weighted_prices

def get_costs(output, model, tech_variable, year_inds):
    """Get the  cost based on the scenario (output), model,
    tech_variable and the indices of the years of interest.
    """
    
    if model == "FTT:P" and tech_variable in [2, 6]:
        prices = output[operation_cost_name[model]][:, tech_variable, 0, year_inds]
    else:
        prices = output[price_names[model]][:, tech_variable, 0, year_inds]

    return prices

def get_weighted_percentage_difference(output, model, 
                                       prices_clean, prices_fossil, year_inds):
    
    """First compute the percentage difference in each region,
    Then compute the weighted difference based on overall market share"""
    
    percentage_difference = get_percentage_difference(prices_clean, prices_fossil)
    weights = np.sum(output[shares_vars[model]][:, :, 0, year_inds], axis=1)    
    weighted_difference = np.average(percentage_difference, weights=weights, axis=0)
    
    return weighted_difference


output_S0 = get_output(output_file, "S0")


#%% =============================================================================
# Cost declines wrt to 2024 at 2035 and 2050 (omitted in favour of different graph)
# ==================================================================================

plot_dot_graph = False

if plot_dot_graph:
    df_dict = {}         # Creates a dict later filled with dataframes

    for model in models:
        df_dict[model] = pd.DataFrame()
        rows = []
        
        # Get the bit of the model name after the colon (like Fr)
        model_abb = model.split(':')[1]
        output_ct = get_output(output_file, f"sxp - {model_abb} CT")
        output_sub = get_output(output_file, f"sxp - {model_abb} subs")
        output_man = get_output(output_file, f"sxp - {model_abb} mand")
        
        scenarios = {"Current traj.": output_S0, "Carbon tax": output_ct,
                     "Subsidies": output_sub, "Mandates": output_man}
        
        for scen, output in scenarios.items():
            weighted_prices = get_weighted_costs(output, model, tech_variable[model], year_inds)
            normalised_prices = weighted_prices / weighted_prices[0]
            
            row = {"Scenario": scen, "Price 2035": normalised_prices[1], "Price 2050": normalised_prices[2]}
            rows.append(row)
        
        df_dict[model] = pd.DataFrame(rows)
        
    
    # Cost declines 2035/2050 -- plotting
    
    fig, axs = plt.subplots(2, 2, figsize=(3.5, 5), sharey=True)
    axs = axs.flatten()
    palette = sns.color_palette("Blues_r", 3)
    
    
    for mi, model in enumerate(models):
        df = df_dict[model]
        ax = axs[mi]
        ax.plot(df["Scenario"], df["Price 2035"], 'o', label='Price 2035', markersize=15, color=palette[0])
        ax.plot(df["Scenario"], df["Price 2050"], 'o', label='Price 2050', markersize=15, color=palette[1])
    
        # Add labels and title
        ax.set_xticklabels(df["Scenario"], rotation=90)
        if mi % 2 == 0:
            ax.set_ylabel('Cost relative to 2024')
        ax.set_title(tech_name[model], pad=20)
        
        # Remove frame
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        ax.xaxis.set_ticks_position('none') 
        ax.yaxis.set_ticks_position('none') 
        
        ax.set_ylim(0.45, 1.)
        ax.grid(axis='y')
        
    
    # Add legend only to the last plot
    handles, labels = ax.get_legend_handles_labels()
    fig.subplots_adjust(hspace=1, wspace=200)
    fig.legend(handles, labels, loc='upper right', frameon=False, ncol=2)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to make space for the legend
    plt.show()
       
    # Save the graph as an editable svg file
    save_fig(fig, fig_dir, "Cost_declines_by_policy")



#%% =====================================================================
# Globally averaged cost difference over time by within-sector policy
# ========================================================================

clean_tech_variable = {"FTT:P": 18, "FTT:Tr": 19, "FTT:H": 10, "FTT:Fr": 13}
fossil_tech_variable = {"FTT:P": 2, "FTT:Tr": 1, "FTT:H": 3, "FTT:Fr": 5} # Note 4 for transport gives an error
graph_label = {"FTT:P": "New solar + battery \n vs existing coal", "FTT:H": "Water-air HP \n vs gas boiler",
               "FTT:Tr": "Electric vehicles \n vs petrol cars", "FTT:Fr": "Electric trucks \n vs diesel trucks"}




   
year_inds = list(range(13, 41))
timeseries_dict = {}


for model in models:
    timeseries_by_policy = []   
    
    # Get the bit of the model name after the colon (like Fr)
    model_abb = model.split(':')[1]
    output_ct = get_output(output_file, f"sxp - {model_abb} CT")
    output_sub = get_output(output_file, f"sxp - {model_abb} subs")
    output_man = get_output(output_file, f"sxp - {model_abb} mand")
    
    scenarios = {"Current traj.": output_S0, "Carbon tax": output_ct,
                 "Subsidies": output_sub, "Mandates": output_man}
     
    
    for scen, output in scenarios.items():
        # weighted_prices_clean = get_weighted_costs(output, model, clean_tech_variable[model], year_inds)
        # weighted_prices_fossil = get_weighted_costs(output, model, fossil_tech_variable[model], year_inds)
        # price_diff_perc = get_percentage_difference(weighted_prices_clean, weighted_prices_fossil)
        # timeseries_by_policy.append(price_diff_perc)
        
        prices_clean = get_costs(output, model, clean_tech_variable[model], year_inds)
        prices_fossil = get_costs(output, model, fossil_tech_variable[model], year_inds)
        price_diff_perc = get_weighted_percentage_difference(output, model, 
                                               prices_clean, prices_fossil, year_inds)
        timeseries_by_policy.append(price_diff_perc)
        if model == "FTT:H":
            test = 1
        
    
    timeseries_dict[model] = timeseries_by_policy

#%% Global cost difference -- plotting
fig, axs = plt.subplots(2, 2, figsize=(3.5, 3.5), sharey=True)
axs = axs.flatten()

# Get 4 colours from the "rocket" palette
colours = sns.color_palette()

def custom_xaxis_formatter(x, pos):
    if x in [2030, 2040]:
        return f'{int(x)}'
    else:
        return ''

for mi, model in enumerate(models):
    ax = axs[mi]

    ax.axhline(y=0, color="grey", linewidth=2)    
    for si, (scen, colour) in enumerate(zip(scenarios.keys(), colours)):
        ax.plot(range(2023, 2051), timeseries_dict[model][si], label=scen, color=colour, linewidth=1)
    
    
    # Remove frame
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    ax.xaxis.set_ticks_position('none') 
    ax.yaxis.set_ticks_position('none') 
    
    if mi in [0, 2, 3]:
        ax.set_xlim(2024, 2030)
        ax.grid(True, which='major', linewidth=0.7)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
    else:
        ax.set_xlim(2024, 2040)
        ax.grid(True, which='major', linewidth=0.7)
        ax.grid(True, which='minor', linewidth=0.2)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(2))

    ax.set_ylim(-5.4, 28)
    # Set the x-axis major ticks to be at intervals of 2 years
       
    
    if mi == 1:
        # Apply the custom formatter to the x-axis
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(custom_xaxis_formatter))
    
    ax.grid(True, axis='y', linewidth=0.5)
    
    if mi == 3:
        ax.legend(loc='right')
    
    if mi in [0, 2]:
        ax.set_ylabel("Levelised cost difference (%)")
    
    #ax.text(2033, 26, graph_label[model], ha="right")
    ax.set_title(graph_label[model], pad=-15, ha="right", fontweight='bold')
    title = ax.title
    title.set_position((0.97, title.get_position()[1]))

    

# Initialize an empty DataFrame to collect the results
df_list = []

years = list(range(2023, 2051))
# Iterate over the dictionary to create the DataFrame
for model, arrays in timeseries_dict.items():
    for i, scenario in enumerate(scenarios.keys()):
        # Convert the array to a DataFrame
        temp_df = pd.DataFrame(arrays[i].reshape(1, -1), columns=years)
        temp_df['Model'] = model
        temp_df['Scenario'] = scenario
        df_list.append(temp_df)
        
# Combine all DataFrames into one
final_df = pd.concat(df_list, ignore_index=True)

# Reorder columns to have 'Model' and 'Scenario' first
final_df = final_df[['Model', 'Scenario'] + years]

# Save the graph and its data
save_fig(fig, fig_dir, "Figure 3 - Global_price_perc_diff_timeseries_by_policy")
save_data(final_df, fig_dir, "Figure 3 - Global_price_perc_diff_timeseries_by_policy")






