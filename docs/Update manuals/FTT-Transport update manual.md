# Instructions for updating FTT: Transport
Ideally, FTT: Transport is updated every year. In particular, it is important to update the share data every year when the latest sales data become available. It is important to update the price and other data in countries undergoing rapid changes in the model variety. Ideally, the history end-year for FTT-Transport should be updated annually. If any updates are made, please ensure that the history end-year is also updated in FTT-Standalone/Utilities/Titles/VariableListing.csv. The current end-year is assumed to be the same for all countries and is set for the year 2022.

## Frequent updates
### Update share data
1. Share data are collected per country and per technology. For EU countries, new vehicle sales data by vehicle technology and size are collected from Eurostat (https://ec.europa.eu/eurostat) directly. For countries outside the EU, the data for new registration per vehicle model type and technology are obtained from MarkLines Information Platform (https://www.marklines.com/portal_top_en.html) (private data that requires an annual subscription, see Note 2 on accessibility) and matched engine and battery sizes, collected from the official websites of the manufacturers (see an example in Note 1). In some cases, when certain models are globally available, it is possible to cross-match technological specifications (e.g. collect engine sizes for the US and use the number for the UK) to speed up the share update process. Marklines data is comprehensive and covers 62 countries around the world.    
2. Then, the next step is to split the sales data by engine size (for ICEVs including PHEVs) or by battery size (kWh). Currently, to be consistent with Eurostat definition, Econ cars are defined as smaller than 1400cc or 30kWh, Mid cars are defined as engine size between 1400cc and 2000cc or battery size between 30 kWh and 70 kWh, and luxury cars are defined as cars with battery size larger than 70 kWh.  
3. the sales data by technology is added to the existing fleet number, considering the historical fleet number (implied in the historical shares)  that needs to be retired from the car population with a survival function. Then, the share by technology can be calculated by fleet number per engine/battery technology. 
4. However, it is not always possible to update all the E3ME/FTT regions shares with Marklines raw data every year since the process can sometimes be time-consuming. In this case, it is possible to refer to IEA EV Data Tool (https://www.iea.org/data-and-statistics/data-tools/global-ev-data-explorer) to obtain the total EV and PHEV numbers in a country and assume that the size in the current year follows the previous years (i.e. follow the size split in the previous years). This process is not always accurate because the EV market is going through a transformation in models (hence the size split may change), but it is better than not carrying out any updates. Please refer to Note 3 for the list of countries currently following Step 1 and the list of countries currently following Step 4. Note 4 will be updated if any changes occur in the share data or if a different approximation is provided.

### Calibration (the gamma values)
Same process as the FTT-Power model. 

### Update cost data 
1. Price data are updated annually (but can be done every two years) for the major regions, including Europe, the US, China, India, Brazil and Japan. For other regions, if not specifically requested, prices are first mapped from a proxy region (e.g. assume that Canada and the US share the same vehicle prices) (see proxy regions in Excel sheet x), then the weighted averages and standard deviation are calculated based on the mapped prices. The mapping processes are currently all done in Excel. Note that price data are collected and processed alongside the engine and technological specification data. Currently, the calculation is carried out in Excel (could be coded in the long run). 
2. Fuel cost: collected GlobalPetrolPrices (https://www.globalpetrolprices.com/); World Bank/IMF prices. 
3. Rare mineral prices: Go to https://www.usgs.gov/centers/national-minerals-information-center/commodity-statistics-and-information and select a mineral (e.g., aluminium at https://www.usgs.gov/centers/national-minerals-information-center/aluminum-statistics-and-information). Then, open the prices and production cost for aluminium at: https://pubs.usgs.gov/periodicals/mcs2023/mcs2023-aluminum.pdf.
   
### Update other technological specification
This is only carried out in countries where cost data are collected because the technological specification is collected alongside prices. 
1. Battery sizes: collected from manufacturers’ websites alongside the prices 
2. Fuel economy (ICEVs) and energy/electricity consumption (EVs): same as above
3. Energy intensity of batteries: from literature such as ICCT and BNEF
4. Battery chemistry: this part requires an annual update because of the rapid changes in battery chemistry

## Less frequent updates
### Other cost data and learning rates
1. Maintenance cost: Collect from a 2021 U.S. Department of Energy comprehensive quantification of total ownership costs, including maintenance costs for BEVs, PHEVs, HEVs, and ICEVs.
2. Update the learning rate. We use learning rates from literature. It is worth updating every 2-3 years for EVs, but more importantly for fuel cell vehicles where learning rates are very uncertain. 
3. Edit the end-years in FTT-Standalone/Utilities/Titles/VariableListing.csv. 

### Technical parameters
5. Mechanical survival rates: Taken from literature for ICEVs and assumed that EVs follow the same survival rates. Updates on the mechanical survival rates for EVs and fuel cell cars are recommended when the data become available

## Notes
### Note 1:
Here is an example of how to search for technological specifications and prices for a car model called the "Corolla Hatchback" from manufacturers' websites for the UK:
Step 1: Go to https://www.toyota.co.uk/.
Step 2: Click on the "Corolla Hatchback" model (https://www.toyota.co.uk/new-cars/corolla-hatchback).
Step 3: Record the prices, fuel economy, and engine size (or battery size/range if it is an EV). In some cases, a car model may have multiple sub-models (variations), so we take the average engine size, prices, and fuel economy.

### Note 2:
Currently, the University of Macau has subscribed to Marklines Data. The subscription allows for two registered users, with the possibility of including more users at a higher cost. In the past, the data were downloaded by one registered user and shared on an online drive for other users involved in processing or using the data. Please contact Aileen Lam if you are interested in accessing Marklines data.

### Note 3: 
The list of countries (E3ME/FTT country number) follows step 1 (for the year 2022): 1-32,34,35,42,42
The list of countries (E3ME/FTT country number) follows step 4 (for the year 2022): 33,36-40,43-70



