# -*- coding: utf-8 -*-
"""
Created on Tue Nov 14 14:55:13 2023

@author: ib400
"""

import chardet
import pandas as pd

# Detect file encoding
with open('Utilities/titles/VariableListing.csv', 'rb') as f:
    result = chardet.detect(f.read())

print(result)

# Read the CSV file with detected encoding
dims_data = pd.read_csv('Utilities/titles/VariableListing.csv', skiprows=0, na_filter=False, encoding=result['encoding'])

# Save the DataFrame to a new CSV file with UTF-8 encoding
dims_data.to_csv('Utilities/titles/VariableListing.csv', index=False, encoding='utf-8')


csv = pd.read_csv('Inputs\S3_1\FTT-P\BCET_AC.csv', header = 0, index_col = 0, encoding = 'utf-8', sep = ',')

csv = pd.read_csv('Inputs\S0\FTT-P\BCET_AC.csv', header=0, index_col = 0, encoding = 'utf-8', sep = ',')
