# -*- coding: utf-8 -*-
"""
US_Local_Backend
Code to handle backend requests for data. Using bottle for server foundations
Last updated 12/2021, 17:10:35
@authors: jp, bkd
"""

# Libraries

from bottle import (route, run, request, response, static_file)
import socket
import glob
import os
import json
import time
import datetime
import csv
import sys
import pandas as pd
import numpy as np

import configparser
from threading import Timer, Thread
import tkinter as tk
from tkinter import messagebox
import psutil
import pickle
from collections import OrderedDict
import SourceCode.support.paths_append
from SourceCode.model_class import ModelRun


#Switch for build
PRODUCTION = True if len(sys.argv) == 1 else False

# File paths
try:
    rundir = sys._MEIPASS
    rootdir = os.path.abspath(sys._MEIPASS)
except AttributeError:
    rootdir = os.path.abspath(os.getcwd())
    rundir = rootdir
switch_dir = "../specs/area1/"
print(rootdir)
print(rundir)
# cache for runs
run_entries_cache = {}

def console_message(error, message, elapsed):
    return str({'error': error, 'message': message,\
         'elapsed_time': elapsed, 'timestamp': str(datetime.datetime.now())})

# the decorator to allow calling the API endpoint from the outside
def enable_cors(fn):
    """Allows for data to be passed between the backend and frontend in a local application"""

    if PRODUCTION:
        return fn
    else:
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            print("CORS set")
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors


p = dict()

@route('/api/run/initialize/', method=['OPTIONS','POST'])
@enable_cors
def init_model():
    """Loads inputs for running the model"""
    body = request.body.read()
    p=json.loads(body.decode("utf-8"))

    global run_entries_cache
    run_entries_cache = p

    return {'status':'true'}

# API endpoint for running the model
#
#   WARNING: this call return an EVENT-STREAM and therefore needs to be handled as such
#   Calling with this function with the proper paramters results in running the model
#   and giving real-time feedback on its progress through server-sent events
#
@route('/api/run/start/', method=['GET'])
@enable_cors
def run_model():
    """Runs the model based on inputs defined in init_model"""

    response.content_type = 'text/event-stream; charset=UTF-8'
    # Load initalised settings
    global run_entries_cache

    entries_to_run = run_entries_cache['data']
    models_to_run =  run_entries_cache['model']
    endyear = str(run_entries_cache['endyear'])

    yield("event: status_change\n")
    yield("data: running\n\n")

    error = False
    yield("event: processing\n")
    # WARNING: hardcoded!

    yield("data: message:Processing started...;\n\n")
    scenarios = [x["scenario"] for x in entries_to_run]
    scenarios = ["S0"] + [x for x in scenarios if x != "S0"]
    models = [x["model"] for x in models_to_run]


    print(",".join(scenarios))
    print(",".join(models))
    # Adjust settings file from frontend parameters
    config = configparser.ConfigParser()
    config.read('settings.ini')
    config.set('settings', 'enable_modules',", ".join(models))
    config.set('settings', 'simulation_end', endyear)
    config.set('settings', 'model_end', endyear)
    config.set('settings', "scenarios",", ".join(scenarios))
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

    #Initalise the model
    model = ModelRun()
    #Define the output based on the inputs
    #TODO: Ensure this matches any revision to model structure changes
    model.output = {scenario: {var: np.full_like(model.input[scenario][var], 0) for var in model.input[scenario]} for scenario in model.input}

    # Defines the number of items to run to track progress (scenarios x year to run)
    yield("data: items;{};\n".format(len(scenarios) * (int(endyear) - model.timeline[0] + 1)))

    scenarios_log = {}
    for scenario in scenarios:

        start_time = time.time()
        yield("event: processing\n")
        yield("data: ;message:Processing {};\n\n".format(scenario))

        try:
            #Solve the model for each year
            for year_index, year in enumerate(model.timeline):
                model.variables, model.lags = model.solve_year(year,year_index,scenario)

                # Populate output container
                for var in model.variables:
                    if 'TIME' in model.dims[var]:
                        model.output[scenario][var][:, :, :, year_index] = model.variables[var]
                    else:
                        model.output[scenario][var][:, :, :, 0] = model.variables[var]

                elapsed_time = time.time() - start_time
                yield("event: processing\n")
                yield("data: progress;{}; \n".format(year))
                yield("data: elapsed;{} \n\n".format(elapsed_time))

                message = 'done'
        except (KeyError, FileNotFoundError) as e:
            error = True
            message = e
            print(e)

        yield("event: processing\n")
        yield("data: message:Finished {};{}; \n\n".format(scenario,message))

        # Update scenario log
        scenarios_log[scenario] = {}
        scenarios_log[scenario]['run'] = datetime.datetime.timestamp(datetime.datetime.now())
        scenarios_log[scenario]['description'] = "Test Scenario, provided by Cambridge Econometrics"
        scenarios_log[scenario]['years'] = [str(x) for x in model.timeline]
        print(scenarios_log)

    run_entries_cache = {}
    # Save output for all scenarios to pickle
    #TODO Setup way to retain older results?
    results =  model.output
    os.makedirs(os.path.dirname(f"{rootdir}\\Output\\"), exist_ok=True)     # Create Output folder if it doesn't exist
    with open('Output\Results.pickle', 'wb') as f:
        pickle.dump(results, f)
    # Save metadata on current model run
    with open("{}\\Output\\Scenarios.json".format(rootdir), 'w') as f:
        json.dump(scenarios_log, f)
    if(error):
        yield("event: processing\n")
        yield("data: message;message:Encountered errors while processing scenarios; \n")
        yield("data: message;message:{}; \n\n".format(message))
        yield("event: status_change\n")
        yield("data: finished_w_errors\n\n")
    else:
        yield("event: processing\n")
        yield("data: message;message:Finished processing scenarios in {}; \n\n".format(elapsed_time))
        yield("event: status_change\n")
        yield("data: finished\n\n")

    return {'done':'true'}


# API endpoint for getting scenarios
#
#   Returns scenarios that can be run from the inputs folder
#
@route('/api/available_scenarios', method=['GET'])
@enable_cors
def available_scenarios():

    list_files_from_results = []


    scenarios  = glob.glob("{}\\inputs\\*\\".format(rootdir))

    scenarios = [s.split("\\")[-2] for s in scenarios]
    scenarios.remove("_MasterFiles")
    list_files_from_results.extend(scenarios)

    list_files_from_results = list(set(list_files_from_results))


    scenids = []
    for scen in list_files_from_results:
        scenid =  {"id":scen,"label":scen}
        scenids.append(scenid)

    models_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name="Models",index_col=0)
    modids = []
    models = models_list["Short name"]
    for mod in models:
        modid =  {"id":mod,"label":mod}
        modids.append(modid)
    return {'scenarios': scenids,'models': modids}

#
#   Returns scenarios that that have been run in latest model run
#
@route('/api/scenarios_ran', method=['GET'])
@enable_cors
def scenarios_ran():

    exist = []
    # Get model run metadata for scenarios
    scenario = "{}\\Output\\Scenarios.json".format(rootdir)
    with open(scenario, 'r+') as f:
        meta = json.load(f)
        for scen,value in meta.items():
            temp = value
            temp["scenario"] = scen
            exist += [temp]
            years = value["years"]


    # Format timestamp for scenarios run
    for e in exist:
        if e['run'] == 0:
            e['Last Run'] = "Never"
        else:
            run_diff = datetime.datetime.fromtimestamp(e['run'])
            current = datetime.datetime.now()
            diff = current - run_diff

            if diff.days > 0:
                e['Last Run'] = "{} days ago".format(diff.days)
            elif diff.seconds / 3600 > 1:
                e['Last Run'] = "{:.0f} hours ago".format(round(diff.seconds / 3600, 0))
            elif diff.seconds / 60 > 1:
                e['Last Run'] = "{:.0f} minutes ago".format(round(diff.seconds / 60, 0))
            else:
                e['Last Run'] = "Seconds ago"
    # Return scenario metadata
    return{'exist':exist,"years":years}

#
# Get the metadata for all model variables
#
@route('/api/results/variables', method=['GET'])
@enable_cors
def retrieve_variables():

    # Load preprocessed metadata file (generated by seprate python script /manager_new/Update manager metadata.py)
    with open('{}//measures_meta.json'.format(rootdir)) as f:
        variable_meta = json.load(f)
    return {'vars': variable_meta}

# API endpoint for getting dimensions for a var for a given county
#
#   returns labels for specific title dimension
#   handles both grouped and ungrouped variables
#
@route('/api/info/<title>', method=['GET'])
@enable_cors
def retrieve_titles(title):
#    agg_all = pd.read_excel("{}\\Utilities\\Titles\\Grouping.xlsx".format(rootdir),sheet_name=None)
#
#    #Check if a dimension has a hierachical structure or not
#    if title in agg_all.keys():
#        with open('{}//manager_new//var_groupings.json'.format(rootdir)) as f:
#            data = json.load(f)
#
#            data = json.dumps({"Sectors": data[title]})
    if title != "None":
        df = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=title)
        df = df.reset_index()
        title_data = list(df['Full name'].unique())

        #Handle numerical titles (like age of technology) and force to string
        if isinstance(title_data[0],np.int64):
            title_data = [str(x) for x in title_data]
        data = json.dumps(title_data)
    else:
        data = json.dumps(["None"])
    return data

# API endpoint for getting all titles used for classification page
#
#   returns a dataframe in JSON format for all model variables
#
@route('/api/info/titles', method=['GET'])
@enable_cors
def retrieve_all_titles():

    title_dict = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=None)
    titles = []
    for t,title in title_dict.items():
        if t=="Cover":
            continue
        title = title.reset_index()

        temp = list(title['Full name'].unique())
        titles.append( {"name":t,"title":[str(x) for x in temp]})

    data = json.dumps(titles)

    return data

# API endpoint for getting all titles used for classification page
#
#   returns a dataframe in JSON format for all model variables
@route('/api/info/vars', method=['GET'])
@enable_cors
def retrieve_var_data():

    vars_meta = pd.read_excel('{}\\Utilities\\Titles\\VariableListing.xlsx'.format(rootdir),sheet_name="Sheet1")
    vars_meta = vars_meta.fillna("None")
    vars_meta_dict = vars_meta.to_dict("records")

    vars_meta = pd.read_excel('{}\\Utilities\\Titles\\VariableListing.xlsx'.format(rootdir),sheet_name="Sheet1")




    return {"items":vars_meta_dict}
    # return pd.DataFrame(list(df['variable'].unique())).to_json()
#
# Function for getting the position of each requested element in a dimension
#

def get_dim_pos(title_code,dims,title):

    #Check if dimension has a hierachy structure with aggregates

    dims_pos = [[title.index(x)] for x in dims]
    return dims_pos
# API endpoint for retrieving model results data
#
#   returns a dataframe in JSON format for the given query parameters
#   paramters should be supported through the parameters object of the request
#
@route('/api/results/data/<type_>', method=['GET'])
@enable_cors
def retrieve_chart_data(type_):

    #Load requests
    p = request.query;

    #extract parameters passed
    variables = p.getlist("variable[]")
    dims = p.getlist("dimensions[]")
    dims2_master = p.getlist("dimensions2[]")
    dims3_master = p.getlist("dimensions3[]")

    title_codes = p.getlist("title[]")
    title2_codes = p.getlist("title2[]")
    title3_codes = p.getlist("title3[]")
    var_labels = p.getlist("variable_label[]")

    scenarios_ = p.getlist("scenarios[]")
    baseline = p.get("baseline")
    agg = p.get("aggregate")
    agg2 = p.get("aggregate2")
    agg3 = p.get("aggregate3")
    calc_type = p.get("calculation")
    time = p.get("time")
    start_year = p.get("Start_Year")
    if start_year != None:
        start_year = int(p.get("Start_Year"))
    end_year = p.get("End_Year")
    if end_year != None:
        end_year = int(p.get("End_Year"))


    # Add baseline to scenarios to extract for calculating difference from baseline
    if baseline not in scenarios_ and calc_type != 'Levels':
        scenarios = scenarios_ + [baseline]
    else:
        scenarios = scenarios_
    full_df = None


    # Load latest model run results
    with open('Output\Results.pickle', 'rb') as f:
        output = pickle.load(f)

    #Get titles
    title_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=None)
    # agg_all = pd.read_excel("{}\\Utilities\\Titles\\Grouping.xlsx".format(rootdir),sheet_name=None,index_col=0)


    # Loop through variables
    for v,var in enumerate(variables):

        #Get variable data
        var_info = json.loads(var_labels[v])
        var_label = var_info["label"]

        #retrieve title codes
        title_code = title_codes[v]
        title2_code = title2_codes[v]
        title3_code = title3_codes[v]

        #Handle null case for spare dimensions otherwise retrieve full
        #titles for each dimension
        if title_code == "None":
            title = ["None"]
        else:
            title = list(title_list[title_code]['Full name'].unique())
        if title2_code == "None":
            title2 = ["None"]
        else:
            title2 = list(title_list[title2_code]['Full name'].unique())
        if title3_code == "None":
            title3 = ["None"]
        else:
            title3 = list(title_list[title3_code]['Full name'].unique())

        #Ensure all titles are strings
        title = [str(x) for x in title]
        title2 = [str(x) for x in title2]
        title3 = [str(x) for x in title3]
        # If all passed then set selection to full list of labels
        if dims2_master[0] == "All":
            dims2 = title2
        else:
            dims2 = dims2_master
        if dims3_master[0] == "All":
            dims3 = title3
        else:
            dims3 = dims3_master
        # Get position of all selected elements in each dimension
        dims_pos = get_dim_pos(title_code,dims,title)
        dims2_pos = get_dim_pos(title2_code,dims2,title2)
        dims3_pos = get_dim_pos(title3_code,dims3,title3)

        # retrieve years of data available from model run metadata
        scen_meta = "{}\\Output\\Scenarios.json".format(rootdir)
        with open(scen_meta, 'r+') as f:
            meta = json.load(f)
            for scen,value in meta.items():
                years = value["years"]

        if time == "Yes":
           years = [str(x) for x in years]
           if start_year!=None and end_year!=None:
               years_filter = [str(x) for x in list(range(start_year,
                                                    end_year + 1))]
           else:
               years_filter = years
        else:
            years = ["None"]


        #Iterate through scenario to extract all request data for the variable
        for scenario in scenarios:
            scenario_df = None

            data = output[scenario]
            data_filter = []
            dims_list = []
            dims2_list = []
            dims3_list = []
            # Loop through all dimensions
            for d1,dim1 in enumerate(dims):
                for d2,dim2 in enumerate(dims2):
                    for d3,dim3 in enumerate(dims3):
                        dims_list.append(dim1)
                        dims2_list.append(dim2)
                        dims3_list.append(dim3)
                        # Extract each element
                        if isinstance(dims_pos[d1],list) or isinstance(dims2_pos[d2],list) or isinstance(dims3_pos[d3],list):
                            #Need to use advanced indexing to cut across multiple dimensions
                            index = np.ix_(dims_pos[d1],dims2_pos[d2],dims3_pos[d3],range(data[var].shape[3]))
                            temp = data[var][index]
                            no_dims = len(temp.shape)
                            sum_cuts = tuple(range(no_dims-1))
                            data_filter.append(np.sum(temp,axis=sum_cuts))
                        else:
                            data_filter.append(data[var][dims_pos[d1],dims2_pos[d2],dims3_pos[d3],:])
            data_filter = np.vstack(data_filter)
            #Convert collected data to dataframe
            df = pd.DataFrame(data_filter,columns=years)
            # Filter years
            df = df.loc[:,years_filter]

            df["dimension"] = dims_list
            df["dimension2"] = dims2_list
            df["dimension3"] = dims3_list
            # Collapse year dimension
            scenario_df = pd.melt(df, id_vars=["dimension","dimension2","dimension3"], value_name="variables")

            #Add additional metadat
            scenario_df['scenario'] = scenario
            scenario_df = scenario_df.rename(columns={"variable":"year"})
            scenario_df["variable"] = var
            scenario_df["Variable Name"] = var_label

            #Collate into single data frame for all scenarios and variables
            #full_df = scenario_df if full_df is None else full_df.append(scenario_df)
            full_df = scenario_df if full_df is None else pd.concat([full_df, scenario_df])

    # Sum across each dimensions if aggregate is set
    if agg == "true":
        full_df = full_df.groupby(['year','scenario',"variable","Variable Name","dimension2","dimension3"]).sum().reset_index().copy()
        full_df["dimension"] = ", ".join(dims)
    if agg2 == "true":
        full_df = full_df.groupby(['year','scenario',"variable","Variable Name","dimension","dimension3"]).sum().reset_index().copy()
        full_df["dimension2"] = ", ".join(dims2)
    if agg3 == "true":
        full_df = full_df.groupby(['year','scenario',"variable","Variable Name","dimension","dimension2"]).sum().reset_index().copy()
        full_df["dimension3"] = ", ".join(dims3)
    # Transform data for difference in baseline
    if calc_type in ['absolute_diff','perc_diff']:
        baseline_df = full_df[full_df['scenario'] == baseline].copy().drop(['scenario'], axis=1)
        full_df = full_df.merge(baseline_df, how="left", left_on=["year","variable","Variable Name","dimension","dimension2","dimension3"], right_on=["year","variable","Variable Name","dimension","dimension2","dimension3"])

        if calc_type == 'absolute_diff':
            full_df["variables"] = full_df.apply(lambda row: row["{}_x".format("variables")] - row["{}_y".format("variables")], axis=1)
        else:
            full_df["variables"] = full_df.apply(lambda row: ((row["{}_x".format("variables")] / row["{}_y".format("variables")]) - 1) *100 if row["{}_y".format("variables")] != 0 else 0 , axis=1)
        # import pdb; pdb.set_trace()
        full_df = full_df.drop(["{}_x".format("variables"),"{}_y".format("variables")], axis=1)

    # Remove baseline data if difference from baseline but baseline is not selected
    if baseline not in scenarios_ and calc_type != 'Levels':
        full_df = full_df[full_df['scenario'] != baseline].copy()

    if calc_type in ['Annual growth rate']:
        if calc_type == 'Annual growth rate':

            full_df['lagged'] = full_df.groupby(['scenario',"variable","Variable Name","dimension","dimension2","dimension3"])["variables"].shift(1)
            full_df["variables"] = (full_df["variables"] / full_df['lagged'] - 1)*100

            full_df = full_df.drop(columns=['lagged'])

    # Handle div zero errors set to 0
    full_df.fillna(0)
    full_df = full_df.reset_index().drop("index",axis=1)

    json_ = full_df.to_json(orient='records')

    piv = full_df.copy()

    dims = ['scenario',"variable","Variable Name",'dimension','dimension2','dimension3']
    dims_all =  ['scenario','year',"variable","variables","Variable Name",'dimension','dimension2','dimension3']

    if type_ == 'csv':
        # Generate csv file for frontend to offer as download
        if time == "Yes":
            piv = piv.pivot_table(index=dims, columns=['year'])
        else:
            piv = piv.pivot_table(index=dims, columns=['dimension3'])
        piv.columns = piv.columns.droplevel(0)
        #If single variable extraction, add a header with metadata
        if len(variables)==1:
            meta_dict = {}
            meta_dict["Variable Name"] = variables[0]
            meta_dict["Desc"] = var_label
            if calc_type == "Annual growth rate" or calc_type == "per_diff" :
                meta_dict["Unit"] = "%"
            else:
                meta_dict["Unit"] = var_info["unit"]
            meta_dict["Type"] = calc_type

            metadata = pd.Series(meta_dict).to_csv(quoting=csv.QUOTE_NONNUMERIC, header=False)

            piv = piv.reset_index().drop(columns=["variable","Variable Name"])
            data = piv.to_csv(quoting=csv.QUOTE_NONNUMERIC,index=False)
            return metadata + data
        else:
            data = piv.to_csv(quoting=csv.QUOTE_NONNUMERIC)
            return data


        return piv.to_csv(quoting=csv.QUOTE_NONNUMERIC)
    else:
        #Generate data for use in front end tables and charts
        piv = piv.drop(columns=list(set(piv.columns)-set(dims_all)))
        if len(variables)==1:
            piv = piv.rename(columns={"variables": variables[0]})
        if time == "Yes":
            piv = piv.pivot_table(index=dims, columns=['year'])
        else:
            piv = piv.pivot_table(index=dims, columns=['dimension3'])
        piv.columns = piv.columns.droplevel(0)

        piv = piv.reset_index()
        if type_ == "json":
            print(piv)
            piv_ = piv.to_json(orient='records', double_precision=4)
            return {'info': list(full_df.columns),'results': json_, 'pivot': piv_}
        #Experimental version for jexcel table
        else:
            piv_ = piv.to_json(orient='values', double_precision=4)
            return {'info': list(full_df.columns),'results': json_, 'pivot': piv_,"pivot_columns": list(piv.columns)}


###Report page queries###

#
# Retrieve list of available report graphics
#
@route('/api/Report/Options', method=['GET'])
@enable_cors
def retrieve_report_graphics():
    graphics = pd.read_excel('{}\\Utilities\\Titles\\ReportGraphics.xlsx'.format(rootdir),
                             sheet_name="Graphic_Definitions",index_col="ref")
    categories = list(set(graphics["Category"]))

    graphics_dict = {}

    for cat in categories:
        cat_df = graphics[graphics["Category"]==cat]
        graphics_dict[cat] = {}

        chart_df = cat_df[cat_df["Type"] == "Chart"]
        #graphic_dict[cat] = cat_df.to_dict(orient="index")
        graphics_dict[cat]["charts"] = list(chart_df["Figure label"])
        table_df = cat_df[cat_df["Type"] == "Table"]
        graphics_dict[cat]["tables"] = list(table_df["Figure label"])
    return{"category": categories, "graphics": graphics_dict}

@route('/api/Report/Values/<graphic>/<type_>', method=['GET'])
@enable_cors
def construct_graphic_data(graphic,type_):


    graphics = pd.read_excel('{}\\Utilities\\Titles\\ReportGraphics.xlsx'.format(rootdir),
                         sheet_name="Graphic_Definitions",index_col="Figure label")
    settings = graphics.loc[graphic.replace("-"," ")]
    command = settings.loc["Vars"].split("|")

    vars = command[1].split(",")

    dims = settings.loc["Dim1"].split(",")
    dims2 = [settings.loc["Dim2"]]
    dims3 = [settings.loc["Dim3"]]

    #Get titles from var listing
    vars_meta = pd.read_excel('{}\\Utilities\\Titles\\VariableListing.xlsx'.format(rootdir),
                              sheet_name="Sheet1",index_col=0)
    #Assume al variables needed have same dimension as first for processing
    vars_meta = vars_meta.fillna("None")

    title_code = vars_meta.loc[vars[0],"Dim1"]
    title2_code = vars_meta.loc[vars[0],"Dim2"]
    title3_code = vars_meta.loc[vars[0],"Dim3"]


    scenarios = ["Baseline"]

    time = "Yes"

    full_df = None

    with open('Output\Results.pickle', 'rb') as f:
        output = pickle.load(f)
    title_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=None)
    # agg_all = pd.read_excel("{}\\Utilities\\Titles\\Grouping.xlsx".format(rootdir),sheet_name=None,index_col=0)
    if title_code == "None":
        title = ["None"]
    else:
        title = list(title_list[title_code]['Full name'].unique())
    if title2_code == "None":
        title2 = ["None"]
    else:
        title2 = list(title_list[title2_code]['Full name'].unique())
    if title3_code == "None":
        title3 = ["None"]
    else:
        title3 = list(title_list[title3_code]['Full name'].unique())

    # Get position of all selected elements in each dimension
    dims_pos = get_dim_pos(title_code,dims,title)
    dims2_pos = get_dim_pos(title2_code,dims2,title2)
    dims3_pos = get_dim_pos(title3_code,dims3,title3)

    scen_meta = "{}\\Output\\Scenarios.json".format(rootdir)
    with open(scen_meta, 'r+') as f:
        meta = json.load(f)
        for scen,value in meta.items():
            years = value["years"]

    if time == "Yes":
       years = [str(x) for x in years]
    else:
        years = ["None"]

    for scenario in scenarios:
        scenario_df = None

        data = output[scenario]
        data_filter = []
        dims_list = []
        dims2_list = []
        dims3_list = []
        var_list = []
        for v,var in enumerate(vars):

            for d1,dim1 in enumerate(dims):
                for d2,dim2 in enumerate(dims2):
                    for d3,dim3 in enumerate(dims3):
                        dims_list.append(dim1)
                        dims2_list.append(dim2)
                        dims3_list.append(dim3)
                        var_list.append(var)
                        if isinstance(dims_pos[d1],list) or isinstance(dims2_pos[d2],list) or isinstance(dims3_pos[d3],list):
                            #Need to use advanced indexing to cut across multiple dimensions
                            index = np.ix_(dims_pos[d1],dims2_pos[d2],dims3_pos[d3],range(data[var].shape[3]))
                            temp = data[var][index]
                            no_dims = len(temp.shape)
                            sum_cuts = tuple(range(no_dims-1))
                            data_filter.append(np.sum(temp,axis=sum_cuts))
                        else:
                            data_filter.append(data[var][dims_pos[d1],dims2_pos[d2],dims3_pos[d3],:])
        data_filter = np.vstack(data_filter)


        df = pd.DataFrame(data_filter,columns=years)
        df["dimension"] = pd.Categorical(dims_list,dims)
        if len(dims2) >1:
            df["dimension2"] = pd.Categorical(dims2_list,dims2)
        else:
            df["dimension2"] = dims2_list
        if len(dims3) >1:
            df["dimension3"] = pd.Categorical(dims3_list,dims3)
        else:
            df["dimension3"] = dims3_list

        df["indic"] = var_list
        scenario_df = pd.melt(df, id_vars=["indic","dimension","dimension2","dimension3"])

        scenario_df['scenario'] = scenario

        full_df = scenario_df if full_df is None else full_df.append(scenario_df)

    full_df = full_df.rename(columns={"variable":"year"})

    #Based on command and time specified transform data
    full_df = full_df.set_index(["indic","dimension","dimension2","dimension3","scenario","year"])
    if command[0] =="DIVIDE":
        #Divde two variables of the same size
        #ustack variable dimension
        full_df = full_df.unstack(level=0).droplevel(0, axis=1)
        #divide variable value columns
        full_df["value"] = full_df.loc[:,vars[0]]/full_df.loc[:,vars[1]]
        #drop divisors
        full_df = full_df.drop(vars,axis=1)
        #Second optional arguement for multiplier
        if len(command) >2:
            full_df = full_df * int(command[2])
    if command[0] == "SHARE":
        #Calculate share of total in each year

        full_df = full_df.unstack(level=-1).droplevel(0, axis=1)
        full_df = full_df/full_df.sum(axis=0)
        #Second optional arguement for multiplier
        if len(command) >2:
            full_df = full_df * int(command[2])

        full_df = pd.melt(full_df.reset_index(), id_vars=["indic","dimension","dimension2","dimension3","scenario"], value_name="value")

    fields = ['scenario','dimension','dimension2','dimension3']

    piv = full_df.pivot_table(index=fields, columns=['year']).droplevel(0, axis=1)
    time_select = settings.loc["Dim4"].split("|")

    for t in time_select:
        if "Growth" in t:
            #Denotes absolute change
            com = t.split(" ")[1]
            coms = com.split("-")
            piv[t] = piv[coms[1]]-piv[coms[0]]
        elif "-" in t:
            #Average annual Percentage growth rate
            coms = t.split("-")
            diff = int(coms[1]) - int(coms[0])
            piv[t] = ((piv[coms[1]]/piv[coms[0]])**(1/diff)-1)*100
    piv = piv.loc[:,time_select]
    for t in piv.columns:
        piv[t] = round(piv[t],settings.loc["decimal_round"])
    full_df = piv.stack().reset_index()

    # Handle div zero errors set to 0
    full_df = full_df.rename(columns={0:"value"})
    full_df["value"].fillna(0)
    full_df.to_csv("Test.csv")

    #full_df.to_csv("Test.csv")
    json_ = full_df.to_json(orient='records')

    piv = full_df.copy()
    #piv['year'] = piv['year'].apply(lambda d_: d_[:4])

    brewer_dict = {}
    #Retrieve all colour codes for brewer
    if settings.loc["Type"] == "Chart":
        label_set = set(time_select + dims + dims2 + dims3)
        label_set.remove("None")

        colours = pd.read_excel('{}\\Utilities\\Titles\\ReportGraphics.xlsx'.format(rootdir),
                             sheet_name="ColoursMap",index_col=0)
        colours.index = [str(x) for x in colours.index]

        rgb_values = pd.read_excel('{}\\Utilities\\Titles\\ReportGraphics.xlsx'.format(rootdir),
                             sheet_name="RGB_values",index_col=0)
        brewer_dict = {}
        colour_codes = [colours.loc[x,"colour_code"] for x in label_set]
        colour_codes_dict = dict(zip( label_set,colour_codes))
        #Handle dual colour classes
        for k,v in colour_codes_dict.items():
            val = str(v)
            if len(val)>2:
                values = val.split("/")
                #Check if first value is already in use
                if values[0] in colour_codes:
                    colour_codes_dict[k] = values[1]
                else:
                    colour_codes_dict[k] = values[0]

        for lab in label_set:
            colour_code = int(colour_codes_dict[lab])
            rgb = "rgb({},{},{})".format(rgb_values.loc[colour_code,"R"],rgb_values.loc[colour_code,"G"],rgb_values.loc[colour_code,"B"])
            brewer_dict[lab] = rgb
    if type_ == 'csv':
        if time == "Yes":
            piv = piv.pivot_table(index=fields, columns=['year'])
        else:
            piv = piv.pivot_table(index=fields, columns=['dimension3'])
        piv.columns = piv.columns.droplevel(0)
        return piv.to_csv(quoting=csv.QUOTE_NONNUMERIC)
    else:
        if time == "Yes":
            piv = piv.pivot_table(index=fields, columns=['year'])
        else:
            piv = piv.pivot_table(index=dims, columns=['dimension3'])
        piv.columns = piv.columns.droplevel(0)

        piv = piv.reset_index()
        if type_ == "json":
            piv_ = piv.to_json(orient='records', double_precision=4)

            return {'info': list(full_df.columns),'results': json_, 'pivot': piv_,
                    "x":settings.loc["x"],"y":settings.loc["y"],"type":settings.loc["Chart type"],
                    "color":settings.loc["color"],"label":settings.loc["label"],"unit":settings.loc["unit"],"brewer":brewer_dict }

#@route('/api/classifications/<code>', method=['GET'])
#@enable_cors
#def get_classification(code):
#    classifications_file = "{}\\Model\\labels\\Classifications.csv".format(rootdir)
#    df = pd.read_csv(classifications_file, quotechar='"')
#    d_ = df[code].pipe(lambda d: d[~d.isna()]).to_dict()
#
#    return {"data": d_}

#
#Deliver the main page of the frontend
#
@route('/main', method=['GET'])
def frontend():
    return static_file("{}\\frontend\\index.html".format(rootdir), "frontend")

@route('/frontend/:filename#.*#', method=['GET'])
def statics(filename):
    return static_file(filename, "{}\\frontend\\".format(rootdir))

#
# Terminate the application
#
@route('/api/exit', method=['GET'])
def exit_():
    q = Timer(2.0, os._exit(1), ())
    return None

# Gamma commands (export to seperate backend)
#Extract baseline Gamma
@route('/api/Gamma/values/<model>/<region>', method=['GET'])
@enable_cors
def load_gamma_values(model, region):
    region_map = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name="RTI",index_col=0)
    title_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name="Models",index_col=0)

    gamma_code = title_list.loc[model,"Gamma_Value"]
    model_folder = title_list.loc[model,"Short name"]

    #load csv
    gamma = pd.read_csv("{}\\Inputs\\S0\\{}\\{}_{}.csv".format(rootdir,model_folder,gamma_code,region_map.loc[region,"Short name"]),
                        skiprows=0,index_col=0)
    gamma = gamma.iloc[:,0]
    gamma_dict = gamma.to_dict()
    gamma_dict = OrderedDict((k,gamma_dict.get(k)) for k in gamma.index)
    return {'gamma': gamma_dict}

@route('/api/info/ftt_options', method=['GET'])
@enable_cors
def retrieve_ftt_options():
    title_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=None,index_col=0)
    ftt_options = list(title_list["Models"].index)
    return json.dumps(ftt_options)

@route('/api/info/region_titles', method=['GET'])
@enable_cors
def retrieve_region_titles():
       df = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name="RTI")
       df = df.reset_index()
       data = json.dumps(list(df['Full name'].unique()))
       return data


# Retrieve data for gamma tool graphics
#TODO Is there a way to merge this into the main graphics function to minimise duplication
@route('/api/gamma/chart/<model>/<region>/<start_year>/<type_>', method=['GET'])
@enable_cors
def construct_gamma_graphic_data(model,region,start_year,type_):



    graphics = pd.read_excel('{}\\Utilities\\Titles\\ReportGraphics.xlsx'.format(rootdir),
                         sheet_name="Gamma_chart",index_col="ref")
    settings = graphics.loc[model]
    command = settings.loc["Vars"].split("|")

    vars = command[1].split(",")

    dims = [region]
    dims3 = [settings.loc["Dim3"]]


    #Get titles from var listing
    vars_meta = pd.read_excel('{}\\Utilities\\Titles\\VariableListing.xlsx'.format(rootdir),
                              sheet_name="Sheet1",index_col=0)
    #Assume al variables needed have same dimension as first for processing
    vars_meta = vars_meta.fillna("None")

    title_code = vars_meta.loc[vars[0],"Dim1"]
    title2_code = vars_meta.loc[vars[0],"Dim2"]
    title3_code = vars_meta.loc[vars[0],"Dim3"]


    scenarios = ["Gamma"]

    time = "Yes"

    full_df = None

    with open('Output\Gamma.pickle', 'rb') as f:
        output = pickle.load(f)

    title_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=None)
    # agg_all = pd.read_excel("{}\\Utilities\\Titles\\Grouping.xlsx".format(rootdir),sheet_name=None,index_col=0)
    if title_code == "None":
        title = ["None"]
    else:
        title = list(title_list[title_code]['Full name'].unique())
    if title2_code == "None":
        title2 = ["None"]
    else:
        title2 = list(title_list[title2_code]['Full name'].unique())
    if title3_code == "None":
        title3 = ["None"]
    else:
        title3 = list(title_list[title3_code]['Full name'].unique())

    dims2 = title2

    # Get position of all selected elements in each dimension
    dims_pos = get_dim_pos(title_code,dims,title)
    dims2_pos = get_dim_pos(title2_code,dims2,title2)
    dims3_pos = get_dim_pos(title3_code,dims3,title3)

    scen_meta = "{}\\Output\\Gamma.json".format(rootdir)
    with open(scen_meta, 'r+') as f:
        meta = json.load(f)
        for scen,value in meta.items():
            years = value["years"]
    if time == "Yes":
       years = [str(x) for x in years]
    else:
        years = ["None"]

    for scenario in scenarios:
        scenario_df = None

        data = output[scenario]
        data_filter = []
        dims_list = []
        dims2_list = []
        dims3_list = []
        var_list = []
        for v,var in enumerate(vars):
            for d1,dim1 in enumerate(dims):
                for d2,dim2 in enumerate(dims2):
                    for d3,dim3 in enumerate(dims3):
                        dims_list.append(dim1)
                        dims2_list.append(dim2)
                        dims3_list.append(dim3)
                        var_list.append(var)
                        if isinstance(dims_pos[d1],list) or isinstance(dims2_pos[d2],list) or isinstance(dims3_pos[d3],list):
                            #Need to use advanced indexing to cut across multiple dimensions

                            index = np.ix_(dims_pos[d1],dims2_pos[d2],dims3_pos[d3],range(data[var].shape[3]))
                            temp = data[var][index]
                            no_dims = len(temp.shape)
                            sum_cuts = tuple(range(no_dims-1))
                            data_filter.append(np.sum(temp,axis=sum_cuts))
                        else:
                            data_filter.append(data[var][dims_pos[d1],dims2_pos[d2],dims3_pos[d3],:])
        data_filter = np.vstack(data_filter)

        df = pd.DataFrame(data_filter,columns=years)
        df["dimension"] = pd.Categorical(dims_list,dims)
        if len(dims2) >1:
            df["dimension2"] = pd.Categorical(dims2_list,dims2)
        else:
            df["dimension2"] = dims2_list
        if len(dims3) >1:
            df["dimension3"] = pd.Categorical(dims3_list,dims3)
        else:
            df["dimension3"] = dims3_list

        df["indic"] = var_list
        scenario_df = pd.melt(df, id_vars=["indic","dimension","dimension2","dimension3"])

        scenario_df['scenario'] = scenario

        full_df = scenario_df if full_df is None else full_df.append(scenario_df)

    full_df = full_df.rename(columns={"variable":"year"})

    #Based on command and time specified transform data
    full_df = full_df.set_index(["indic","dimension","dimension2","dimension3","scenario","year"])
    if command[0] =="DIVIDE":
        #Divde two variables of the same size
        #ustack variable dimension
        full_df = full_df.unstack(level=0).droplevel(0, axis=1)
        #divide variable value columns
        full_df["value"] = full_df.loc[:,vars[0]]/full_df.loc[:,vars[1]]
        #drop divisors
        full_df = full_df.drop(vars,axis=1)
        #Second optional arguement for multiplier
        if len(command) >2:
            full_df = full_df * int(command[2])
    if command[0] == "SHARE":
        #Calculate share of total in each year

        full_df = full_df.unstack(level=-1).droplevel(0, axis=1)
        full_df = full_df/full_df.sum(axis=0)
        #Second optional arguement for multiplier
        if len(command) >2:
            full_df = full_df * int(command[2])

        full_df = pd.melt(full_df.reset_index(), id_vars=["indic","dimension","dimension2","dimension3","scenario"], value_name="value")

    fields = ['scenario','dimension','dimension2','dimension3']

    piv = full_df.pivot_table(index=fields, columns=['year']).droplevel(0, axis=1)
    time_select = [str(x) for x in list(range(max(int(piv.columns[0]),int(start_year)),int(piv.columns[-1])+1))]

    for t in time_select:
        if "Growth" in t:
            #Denotes absolute change
            com = t.split(" ")[1]
            coms = com.split("-")
            piv[t] = piv[coms[1]]-piv[coms[0]]
        elif "-" in t:
            #Average annual Percentage growth rate
            coms = t.split("-")
            diff = int(coms[1]) - int(coms[0])
            piv[t] = ((piv[coms[1]]/piv[coms[0]])**(1/diff)-1)*100

    piv = piv.loc[:,time_select]

    for t in piv.columns:
        piv[t] = round(piv[t],settings.loc["decimal_round"])
    full_df = piv.stack().reset_index()

    # Handle div zero errors set to 0
    full_df = full_df.rename(columns={0:"value"})
    full_df["value"].fillna(0)

    json_ = full_df.to_json(orient='records')

    piv = full_df.copy()

    dims_all =  ['scenario','year','dimension','dimension2','dimension3']
    print(piv)
    if type_ == 'csv':
        if time == "Yes":
            print(piv)
            piv = piv.pivot_table(index=fields, columns=['year'])
        else:
            piv = piv.pivot_table(index=fields, columns=['dimension3'])
        piv.columns = piv.columns.droplevel(0)
        return piv.to_csv(quoting=csv.QUOTE_NONNUMERIC)
    else:
        if time == "Yes":
            piv = piv.pivot_table(index=fields, columns=['year'])
        else:
            piv = piv.pivot_table(index=dims, columns=['dimension3'])
        piv.columns = piv.columns.droplevel(0)

        piv = piv.reset_index()
        piv = piv.drop("dimension3", axis=1)
        if type_ == "json":

            piv_ = piv.to_json(orient='records', double_precision=4)
            return {'info': list(full_df.columns),'results': json_, 'pivot': piv_,
                    "x":settings.loc["x"],"y":settings.loc["y"],"type":settings.loc["Chart type"],
                    "color":settings.loc["color"],"label":settings.loc["label"],"unit":settings.loc["unit"] }


#Initialise model run with updated Gamma value to scenario
@route('/api/run_gamma/initialize/<end_year>', method=["GET"])
@enable_cors
def init_model(end_year):

    global run_entries_cache
    run_entries_cache = p

    # Save Gamma value passed

    entries_to_run = ["Gamma"]
    endyear = str(end_year)


    config = configparser.ConfigParser()
    config.read('settings.ini')
    config.set('settings', 'simulation_end', endyear)
    config.set('settings', 'model_end', endyear)
    config.set('settings', 'scenarios', "S0, Gamma")
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)
    print (entries_to_run)

    global model
    model = ModelRun()
    years = list(model.timeline)
    years = [int(x) for x in years]


    return {'status':'true',"years":years }


# Updates gamma values in memory for current model run
@route('/api/run_gamma/update_gamma/', method=['OPTIONS','POST'])
@enable_cors
def load_gamma():
    body = request.body.read()
    p=json.loads(body.decode("utf-8"))
    gamma = p['data']
    ftt = p["model"]
    reg_pos = int(p['region_pos'])

    gamma_values = list(gamma.values())

    config = configparser.ConfigParser()
    config.read('settings.ini')

    title_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=None,index_col=0)
    models = title_list["Models"]
    gamma_code = models.loc[ftt,"Gamma_Value"]
    model_folder = models.loc[ftt,"Short name"]


    model.input["Gamma"][gamma_code][reg_pos,:,0,:] = np.array(gamma_values).reshape(-1,1)
    config.set('settings', 'enable_modules', model_folder)

    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

    return {'status':'true'}

# Saves gamma values to baseline inputs csv
@route('/api/run_gamma/save_gamma/', method=['OPTIONS','POST'])
@enable_cors
def save_gamma():
    body = request.body.read()
    p=json.loads(body.decode("utf-8"))
    gamma = p['data']
    region = p['region']
    ftt = p["model"]
    gamma_values = list(gamma.values())

    #Copy gamma file from baseline to gamma
    title_list = pd.read_excel('{}\\Utilities\\Titles\\classification_titles.xlsx'.format(rootdir),sheet_name=None,index_col=0)
    reg = title_list["RTI"].loc[region,"Short name"]
    models = title_list["Models"]
    gamma_code = models.loc[ftt,"Gamma_Value"]
    model_folder = models.loc[ftt,"Short name"]

    gamma_file = "{}_{}.csv".format(gamma_code,reg)
    base_dir = "Inputs\\S0\\{}\\".format(model_folder)

    gamma_df = pd.read_csv(os.path.join(rootdir,base_dir,gamma_file),index_col=0)
    gamma_df.loc[:,:] = np.array(gamma_values).reshape(-1,1)

    gamma_df.to_csv(os.path.join(rootdir,base_dir,gamma_file))

    return {'status':'true'}

#run the specific gamma scenario run
#TODO generalise run model command for general and gamma specific case to remove duplication

@route('/api/run_gamma/start/', method=['GET'])
@enable_cors
def run_model():
    response.content_type = 'text/event-stream; charset=UTF-8'
    global run_entries_cache

    entries_to_run = ["Gamma"]
    yield("event: status_change\n")
    yield("data: running\n\n")

    error = False
    yield("event: processing\n")
    # WARNING: hardcoded!

    yield("data: message:Processing started...;\n\n")

    # Adjust settings file from frontend parameters
    config = configparser.ConfigParser()
    config.read('settings.ini')
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)
    print (entries_to_run)
    scenarios =  entries_to_run

    model.timeline = np.arange(model.simulation_start, model.model_end+1)
    model.ftt_modules = config.get('settings', 'enable_modules')
    print(model.ftt_modules )
    print(model.timeline)

    model.output = {scenario: {var: np.full_like(model.input[scenario][var], 0) for var in model.input[scenario]} for scenario in model.input}
    yield("data: items;{};\n".format(len(entries_to_run) * (model.timeline[-1] - model.timeline[0])))
    print(model.timeline[0])
    scenarios_log = {}
    for scenario in scenarios:


        start_time = time.time()
        # time.sleep(1)
        yield("event: processing\n")
        yield("data: ;message:Processing {};\n\n".format(scenario))

        try:
            #Solve the model for each year
            for year_index, year in enumerate(model.timeline):
                model.variables, model.lags = model.solve_year(year,year_index,scenario)

                # Populate output container
                for var in model.variables:
                    if 'TIME' in model.dims[var]:
                        model.output[scenario][var][:, :, :, year_index] = model.variables[var]
                    else:
                        model.output[scenario][var][:, :, :, 0] = model.variables[var]

                elapsed_time = time.time() - start_time
                yield("event: processing\n")
                yield("data: progress;{}; \n".format(year))
                yield("data: elapsed;{} \n\n".format(elapsed_time))

                message = 'done'
        except (KeyError, FileNotFoundError) as e:
            error = True
            message = e
            print(e)

        yield("event: processing\n")
        yield("data: message:Finished {};{}; \n\n".format(scenario,message))

        # Update scenario log
        scenarios_log[scenario] = {}
        scenarios_log[scenario]['run'] = datetime.datetime.timestamp(datetime.datetime.now())
        scenarios_log[scenario]['description'] = "Test Scenario, provided by Cambridge Econometrics"
        scenarios_log[scenario]['years'] = [str(x) for x in model.timeline]
        print(scenarios_log)

    run_entries_cache = {}
    results =  model.output
    with open('Output\Gamma.pickle', 'wb') as f:
        pickle.dump(results,f)
    with open("{}\\Output\\Gamma.json".format(rootdir), 'w') as f:
        json.dump(scenarios_log, f)
    if(error):
        yield("event: processing\n")
        yield("data: message;message:Encountered errors while processing scenarios; \n")
        yield("data: message;message:{}; \n\n".format(message))
        yield("event: status_change\n")
        yield("data: finished_w_errors\n\n")
    else:
        yield("event: processing\n")
        yield("data: message;message:Finished processing scenarios in {}; \n\n".format(elapsed_time))
        yield("event: status_change\n")
        yield("data: finished\n\n")

    return {'done':'true'}

# MAIN APP
# ==========

message_cache = []

if __name__ == '__main__':

    def splash():
        root = tk.Tk()
        root.overrideredirect(True)
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()

        img_width = 533
        img_height = 300

        x0 = width / 2 - img_width / 2
        x1 = width / 2 + img_width / 2
        y0 = height / 2 - img_height / 2
        y1 = height / 2 + img_height / 2

        root.geometry('%dx%d+%d+%d' % (img_width, img_height, x0, y0))
        root.attributes("-alpha", 0.9)

        if os.path.exists("{}//splash.png".format(rootdir)):
            image_file = "{}//splash.png".format(rootdir)
        else:
            image_file = "{}//splash.png".format(rundir)

        image = tk.PhotoImage(file=image_file)
        canvas = tk.Canvas(root, height=img_height, width=img_width)
        canvas.create_image(0, 0, image=image, anchor=tk.NW)
        canvas.pack()
        # show the splash screen for 5000 milliseconds then destroy
        root.after(5000, root.destroy)
        root.call('wm', 'attributes', '.', '-topmost', '1')
        root.mainloop()
    # splash()

    # testing if the given port is available, if not, test other ones
    bport = 5000  # base port number, to be added on to
    success = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for jj in range(100):
        port = bport + jj
        try:
            s.bind(('127.0.0.1', port))
            success = True
            s.close()
            break
        except socket.error as e:
            # print(e)
            continue

    if not success:
        raise IOError('Failed to open a port, the front end will not start.')

    port = 5000
    addr = 'http://localhost:%s' % port
    if PRODUCTION:

        already_running = False
        count = 0
        for p in psutil.process_iter(attrs=['pid', 'name']):
            if "CE_LEM_Launcher.exe" in p.info['name']:
                count += 1
                if count > 1:
                    root = tk.Tk()
                    root.withdraw()
                    if messagebox.askokcancel("Error","Application already running. Do you want to go to the running instance?"):
                        os.system("start {}/main".format(addr))
                    os._exit(1)

        start = lambda: run(host='localhost', port=int(port), server='paste', reloader=False)
        thr = Thread(target=start)
        thr.setDaemon(True)
        thr.start()

        os.system("start {}/main".format(addr))

    else:
        print("Manager running in development mode...")
        run(host='localhost', port=int(port), server='paste', reloader=True)
