# Instructions for updating FTT-Freight
Author - c.lynch4@exeter.ac.uk

FTT-Freight is a fairly simple FTT model that simulates technology uptake and competition amongst three-wheeler freight vehicles (India only), light-commercial vehicles (vans), medium duty truck, heavy duty trucks, and buses. Because of the very different technology types represented in the model, we chose to prohibit decision-makers switching between vehicle segments. This means a decision-maker cannot replace a diesel LCV with a battery electric bus. As a result, each vehicle segment has its own demand profile and should be considered seperate from one another.
Updating FTT-Freight is similar to FTT-Transport. With the exception of the [IEA's EV outlook](https://www.iea.org/data-and-statistics/data-tools/global-ev-data-explorer), publically available data is not readily available. Instead, the model makes use of data from the ICCT. A data processing script can be found in the FTT_Standalone-support repository.

## Aggregate fleet sizes (RFLZ)
1. Each vehicle segment has its own projections for fleet size. 
2. The ICCT provides fleet size projections from its Roadmap model for Canada, China, the EU, India, and the US. This covers the period 2020-2050. Using a combination of these projections and historical stock data, we backward extrapolate fleet size to 2010.
3. We further disaggregate the EU projections into EU member states using the split of fleet sizes obtained from the historical stock data (2018-2023).
4. For regions outside of the ICCT's coverage, we apply a rough fleet size estimation based on economic output from the 'Land Transport' sector in E3ME. This is where road freight (among other things) is accounted for in economies. For the countries we do have stock data for, we derive an approxmiate ratio of 45 freight vehicles to 1 million euro of output in this sector. Fleet size numbers for major missing economies (Brazil, Japan, Russia) are checked to verify rough accuracy.
5. The estimated fleet sizes are then split by vehicle segment. We apply the EU's average vehicle splits (that change over time) in regions such as the UK, Japan, and Korea. We apply the US segment splits elsewhere.
6. FTT-Freight also includes three-wheeler freight vehicles in India. As this segment is not included in the ICCT's projections, we estimate three-wheeler stock growth by extrapolating the size of the fleet from the period 2016-2023 where data is provided by WRI-India. 

## Market shares (ZEWS)
1. Historical stock is sourced from the ICCT for China and India (2020-2023) and the EU (at member state level) and the US (2018-2023).
2. Additional stock data on three-wheeler freight vehicles in India is provided by WRI India (2016-2023).
3. Stock is backward extrapolated to 2010 and market shares are calculated. Shares are not a function of the total national stock but rather the share of the total segment stock. Because of this, market shares for a region should sum to 4 (or 5 in India because of three-wheelers) to reflect the number of vehicle segments.
4. For countries without ICCT stock data, we assign shares based on similar freight markets. Australia, Canada, and New Zealand use the same shares as the US. The UK, Norway, Switzerland, Iceland, Japan, and Korea use EU shares. Mexico, Brazil, and Argentina use the US' shares but with 1/2 the number of electric vehicles. Turkey, Macedonia, and Taiwan use the EU's shares but with 1/2 the number of electric vehicles. All other regions use the US' shares but with no electric vehicles assumed.
5. To provide improved data pre-2020 and to improve data quality in some non-ICCT regions, we add in data from the IEA's EV outlook. We prioritise ICCT data where we have it, but when we must extrapolate or use proxies, we overwrite these estimates with the IEA's numbers. This is particularly valuable for regions like the UK, Japan, and Brazil that are not included in the ICCT dataset.
6. The IEA data does not split 'trucks' into medium and heavy duty like the ICCT does. We therefore use data on the split of medium to heavy duty electric trucks observed in the ICCT data and apply this to the IEA data.
7. The IEA data also only provides data on the market share of electric (includes battery electric, plug-in hybrid, and fuel cell) vehicles. We therefore only override estimates for these powertrains and then adjust the market shares of other technologies to ensure shares still sum to 1 within a vehicle segment (i.e., buses).

## Investment and O&M costs
1. 

## Fuel costs
1. 

## Freight/passenger demand
1. 

## Learning rate
1. 
