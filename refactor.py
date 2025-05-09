import streamlit as st
import pandas as pd
import re
from io import BytesIO

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------
def determine_status(row):
    mapping = {
        (1,1): 'CURRENT',  (2,2): 'FEA USD',  (2,3): 'FCA USD',
        (1,4): 'EASY SAVERS', (4,3): 'FCA EUR', (3,2): 'FEA GBP',
        (4,2): 'FEA EUR', (1,55): 'CALL'
    }
    return mapping.get((row.CUR_CODE, row.LED_CODE), 'FCA GBP')


def filter_category(df, patterns):
    pattern = '|'.join(map(re.escape, patterns))
    return df[df['CUS_SHO_NAME'].str.contains(pattern, case=False, na=False)].copy()


def prepare_df(df, patterns, threshold):
    subset = filter_category(df, patterns)
    subset = subset[subset.CRNT_BAL > threshold]
    subset['TYPE_OF_EXPOSURE'] = subset.apply(determine_status, axis=1)
    return subset


def to_excel(dfs):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    for sheet, df in dfs.items():
        df.to_excel(writer, sheet_name=sheet, index=False)
    writer.close()
    return output.getvalue()

# ------------------------------------------------------------------
# Streamlit App
# ------------------------------------------------------------------
st.title("Exposures to BoG")

# File upload
uploaded_file = st.file_uploader("Upload exposures Excel", type=['xlsx'])
if not uploaded_file:
    st.info("Please upload an Excel file to proceed.")
    st.stop()

# Settings sidebar
st.sidebar.header("Settings")
balance_threshold = st.sidebar.number_input("Minimum CRNT_BAL", value=5, min_value=0, step=1)

# Load data
@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_excel(file)
    cols = ['BRA_CODE','CUS_NUM','CUS_SHO_NAME','CUR_CODE','LED_CODE',
            'SUB_ACCT_CODE','CRNT_BAL','TYPE_OF_DEP']
    return df[cols]

exposures = load_data(uploaded_file)

# Define category patterns
categories = {
    'Insurance': {'patterns': ['Enterprise Group'], 'by_type_dep': True},
    'Pensions': {'patterns': ['Pens','Pension','Petra']},
    'Securities & Exchange': {'patterns': ['Securit']},
    'Savings & Loans': {'patterns': ['Saving']},
    'MicroFinance': {'patterns': ['Micro-Finance', "M'Finance", 'MicroFinance','Micro Finance']},
    'Finance Houses': {'patterns': ['Capital','Investment','Income','Finance','Databank','Fund','Obsidian','Stanlib','Zeepay']},
    'Rural Bank': {'patterns': ['Rural Bank']},
    'Credit Union': {'patterns': ['Credit Union','Cop','co-op','BACCSOD']},
    'Money Lending': {'patterns': ['micro-credit','susu','lending']},
    'Mortgage Institutions': {'patterns': ['propert','estate','building','engineer']}
}

# Process each category
results = {}
for name, cfg in categories.items():
    if cfg.get('by_type_dep'):
        df1 = exposures[exposures.TYPE_OF_DEP == 28]
        df1 = df1[df1.CRNT_BAL > balance_threshold]
        df1['TYPE_OF_EXPOSURE'] = df1.apply(determine_status, axis=1)
        df2 = filter_category(exposures, cfg['patterns'])
        df2 = df2[df2.CRNT_BAL > balance_threshold]
        df2['TYPE_OF_EXPOSURE'] = df2.apply(determine_status, axis=1)
        results[name] = pd.concat([df1, df2])
    else:
        results[name] = prepare_df(exposures, cfg['patterns'], balance_threshold)

# Category selection dropdown
selected = st.selectbox("Select Category to Preview", list(results.keys()))
preview_df = results[selected]

# Display preview
st.subheader(f"{selected} (n={len(preview_df)})")
st.dataframe(preview_df)

# Single download button for all categories
xlsx_data = to_excel(results)
st.download_button(
    label="Download All Categories as Excel",
    data=xlsx_data,
    file_name=uploaded_file.name.replace('.xlsx', '_processed.xlsx'),
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)
