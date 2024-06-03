'''Code snippets which will be useful for gamma automation'''



from SourceCode.model_class import ModelRun
model = ModelRun()
model.timeline = np.arange(model.simulation_start, model.model_end+1)
years = list(model.timeline)
years = [int(x) for x in years]
model.output = {scenario: {var: np.full_like(model.input[scenario][var], 0) for var in model.input[scenario]} for scenario in model.input}
for year_index, year in enumerate(model.timeline):
                model.variables, model.lags = model.solve_year(year,year_index,scenario)

                # Populate output container
                for var in model.variables:
                    if 'TIME' in model.dims[var]:
                        model.output[scenario][var][:, :, :, year_index] = model.variables[var]
                    else:
                        model.output[scenario][var][:, :, :, 0] = model.variables[var]


def rate_of_change(shares):
    shares_dot = shares[t] - shares[t-1]