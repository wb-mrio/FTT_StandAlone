import pandas as pd


shares = pd.read_csv("Gamma Value Automation/IWS1_AT.csv")

shares_lag = shares.copy()
shares_lag.iloc[:,1:] = shares.iloc[:,1:].shift(1, axis=1)

shares_dt = shares.copy()
shares_dt.iloc[:,1:] = shares.iloc[:,1:] - shares_lag.iloc[:,1:] 

shares_dt.pop("2000")

shares_dt.to_csv("Gamma Value Automation/IDS1_AT.csv")