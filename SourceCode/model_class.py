# -*- coding: utf-8 -*-
"""
=========================================
model_class.py
=========================================

Model Class file for FTT Stand alone.


ModelRun class: main class for operation of model.

"""

# Standard library imports
import configparser
import copy

# Third party imports
import numpy as np
from tqdm import tqdm

# Local library imports
# Separate FTT modules
import SourceCode.Power.ftt_p_main as ftt_p
import SourceCode.Transport.ftt_tr_main as ftt_tr
import SourceCode.Heat.ftt_h_main as ftt_h
#import SourceCode.Steel.ftt_s_main as ftt_s
#import SourceCode.Agri.ftt_agri_main as ftt_agri
import SourceCode.Freight.ftt_fr_main as ftt_fr
#import SourceCode.Flex.ftt_flex_main as ftt_flex
#import SourceCode.Hydrogen.ftt_h2_main as ftt_h2
import SourceCode.Industrial_Heat.ftt_chi_main as ftt_indhe_chi
import SourceCode.Industrial_Heat.ftt_fbt_main as ftt_indhe_fbt
import SourceCode.Industrial_Heat.ftt_mtm_main as ftt_indhe_mtm
import SourceCode.Industrial_Heat.ftt_nmm_main as ftt_indhe_nmm
import SourceCode.Industrial_Heat.ftt_ois_main as ftt_indhe_ois2
from SourceCode.sector_coupling.electricity_price import electricity_price_feedback
from SourceCode.sector_coupling.electricity_demand import electricity_demand_feedback



# Support modules
import SourceCode.support.input_functions as in_f
import SourceCode.support.titles_functions as titles_f
import SourceCode.support.dimensions_functions as dims_f
from SourceCode.support.cross_section import cross_section as cs
from SourceCode.initialise_csv_files import initialise_csv_files


class ModelRun:
    """
    Class to run the FTT model.

    Class object is a single run of the model.

    Local library imports:

        FTT modules:

        - `FTT: Power <ftt_p_main.html>`__
            Power generation FTT module
        - `FTT: Transport <ftt_tr_main.html>`__
            Transport FTT module
        - `FTT: Freight <ftt_fr_main.html>`__
            Freight FTT module
        - `FTT: Heat <ftt_h_main.html>`__
            Heat FTT module
        - `FTT: IndHe CHI <ftt_chi_main.html>`__
            Industrial heat - chemicals FTT module
        - `FTT: IndHe FBT <ftt_fbt_main.html>`__
            Industrial heat - food, beverages, and tobacco FTT module
        - `FTT: IndHe MTM <ftt_mtm_main.html>`__
            Industrial heat - non-ferrous metals, machinery, and transport equipment FTT module
        - `FTT: IndHe NMM <ftt_nmm_main.html>`__
            Industrial heat - non-metallic minerals FTT module
        - `FTT: IndHe OIS <ftt_ois_main.html>`__
            Industrial heat - other sectors FTT module


        Support functions:

        - `paths_append <paths_append.html>`__
            Appends file path to sys path to enable import
        - `divide <divide.html>`__
            Bespoke element-wise divide which replaces divide-by-zeros with zeros

    Attributes
    -----------
    name: str
        Name of model run, and specification file read
    hist_start: int
        Starting year of the historical data
    model_start: int
        First year of model timeline
    model_end: int
        Final year of model timeline
    current: int
        Current/active year of solution
    years: tuple of (int, int)
        Bookend years of model_timeline
    timeline: list of int
        Years of the model timeline
    titles: dictionary of lists
        Dictionary containing all title classifications
    dims: dict of tuples (str, str, str, str)
        Variable classifications by dimension
    histend: dict of integers
        Final year of histrorical data by variable
    specs: dictionary of NumPy arrays
        Function specifications for each region and module
    input: dictionary of NumPy arrays
        Dictionary containing all model input variables
    variables: dictionary of NumPy arrays
        Dictionary containing all model variables for a given year of solution
    lags: dictionary of NumPy arrays
        Dictionary containing lag variables
    output: dictionary of NumPy arrays
        Dictionary containing all model variables for output



    """

    def __init__(self):
        """ Instantiate model run object """

        # Attributes given in settings.ini file
        config = configparser.ConfigParser()
        config.read('settings.ini')
        self.name = config.get('settings', 'name')
        self.model_start = int(config.get('settings', 'model_start'))
        self.model_end = int(config.get('settings', 'model_end'))
        self.simulation_start = int(config.get('settings', 'simulation_start'))
        self.simulation_end = int(config.get('settings', 'simulation_end'))
        self.current = self.model_start
        self.years = np.arange(self.model_start, self.model_end+1)
        self.timeline = np.arange(self.simulation_start, self.simulation_end+1)
        self.ftt_modules = config.get('settings', 'enable_modules')
        self.scenarios = config.get('settings', 'scenarios')

        # Load classification titles
        self.titles = titles_f.load_titles()

        # Load variable dimensions
        self.dims, self.histend, self.domain, self.forstart, self.unit = dims_f.load_dims()
        
        # Set up csv files if they do not exist yet
        initialise_csv_files(self.ftt_modules, self.scenarios)
        
        # Retrieve inputs
        self.input = in_f.load_data(self.titles, self.dims, self.timeline,
                                    self.scenarios, self.ftt_modules,
                                    self.forstart)


        # Initialize remaining attributes
        self.variables = {}
        self.lags = {}
        self.output = {}


    def run(self):
        """ Solve model run and save results """

        # Run the solve all method (self.input contains all results)
        self.solve_all()

    def solve_all(self):
        """ Solve model for each year of the simulation period """

        # Define output container
        self.output = {scen: {var: np.full_like(self.input[scen][var], 0) \
                              for var in self.input[scen]} for scen in self.input}

        # Clear any previous instances of the progress bar
        try:
            tqdm._instances.clear()
        except AttributeError:
            pass
        
        for scen in self.input:

            # Create progress bar:
            with tqdm(self.timeline) as pbar:

                # Call solve_year method for each year of the simulation period
                for y, year in enumerate(self.timeline):
                    # Set the description to be the current year
                    pbar.set_description(f'Running Scenario: {scen} - Solving year: {year}')

                    self.variables, self.lags = self.solve_year(year, y, scen)

                    # Increment the progress bar by one step
                    pbar.update(1)
                    try:
                        # Populate output container
                        for var in self.variables:
                            if 'TIME' in self.dims[var]:
                                self.output[scen][var][:, :, :, y] = self.variables[var]
                            else:
                                self.output[scen][var][:, :, :, 0] = self.variables[var]
                    except ValueError as e:
                        print(f"Error in scenario {scen} and variable {var}")
                        raise(e)

            # Set the progress bar to say it's complete
            pbar.set_description(f"Model run {self.name} finished")

    def solve_year(self, year, y, scenario, max_iter=1):
        """ Solve model for a specific year """

        # Need to add a convergence check here in the future

        # Run update
        variables, time_lags = self.update(year, y, scenario)
        iter_lags = copy.deepcopy(time_lags)

        # Define whole period
        tl = self.timeline

        # define modules list in for possible setting.ini selection
        modules_list = ["FTT-P","FTT-Fr","FTT-Tr","FTT-H","FTT-S","FTT-IH-CHI","FTT-IH-FBT",
                    "FTT-IH-MTM","FTT-IH-NMM","FTT-IH-OIS"]
        # Iteration loop here
        for itereration in range(max_iter):

            
            if "FTT-Tr" in self.ftt_modules:
                variables = ftt_tr.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
            if "FTT-Fr" in self.ftt_modules:
                variables = ftt_fr.solve(variables, time_lags, 
                                        self.titles, self.histend, tl[y],
                                        self.domain)
            if "FTT-H" in self.ftt_modules:
                variables = ftt_h.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
            if "FTT-S" in self.ftt_modules:
                print("Module needs to be created")
            if "FTT-IH-CHI" in self.ftt_modules:
                variables = ftt_indhe_chi.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
                
            if "FTT-IH-FBT" in self.ftt_modules:
                variables = ftt_indhe_fbt.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
                
            if "FTT-IH-MTM" in self.ftt_modules:
                variables = ftt_indhe_mtm.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
                
            if "FTT-IH-NMM" in self.ftt_modules:
                variables = ftt_indhe_nmm.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
                
            if "FTT-IH-OIS2" in self.ftt_modules:
                variables = ftt_indhe_ois2.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
                
            if scenario != "S0":
                if year > 2022:
                    variables = electricity_demand_feedback(variables, 
                                        self.output["S0"], y, self.titles,
                                        self.unit)
            
            if "FTT-P" in self.ftt_modules:
                variables = ftt_p.solve(variables, time_lags, iter_lags,
                                        self.titles, self.histend, tl[y],
                                        self.domain)
            
            if "FTT-P" in self.ftt_modules:
                if year > 2022:
                    variables = electricity_price_feedback(variables, time_lags)
                
            if not any(True for x in modules_list if x in self.ftt_modules):
                print("Incorrect selection of modules. Check settings.ini")

            # Third, solve energy supply
            # Overwrite iter_lags to be used in the next iteration round
            iter_lags = copy.deepcopy(variables)
#        # Print any diagnostics
#
        return variables, time_lags

    def update(self, year, y, scenario):
        """ Update model variables for a new year of solution """

        # Update the current year attribute
        self.current = year

        # Set any required variables as equal to the previous year
        # This is how E3ME solves a number of variables, return to this

        # Read required variables from the cross section
        # This is how E3ME solves a number of variables, return to this
        data_to_model = cs(self.input, self.dims, year, y, scenario)

        # LB TODO: to improve the treatment of lags to include also historical data
        if y == 0: # In the first year, lags equal variables in starting year
            lags = cs(self.input, self.dims, year, y, scenario)
        else:
            #lags = cs(self.variables, self.dims, year-1)
            lags = self.variables

        return data_to_model, lags
