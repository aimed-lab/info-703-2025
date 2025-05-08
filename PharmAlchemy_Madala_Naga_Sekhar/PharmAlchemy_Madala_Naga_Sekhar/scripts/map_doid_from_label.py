#!/usr/bin/env python3
"""
Map DOID to DisGeNET disease tables using HumanDO_ontology_mapped.csv (LABEL→DOID).

This script adds a 'doid' column to:
  1. disgenet_disease_mapped.csv → disgenet_disease_mapped_DO.csv
  2. d2r_disgenet.csv           → d2r_disgenet_DO.csv

It matches on:
  • disease_name (in disgenet_disease_mapped.csv)
  • concept_name (in d2r_disgenet.csv)

Outputs are also copied to apex_upload/ for seamless APEX import.
"""
from pathlib import Path
import pandas as pd

# ————— CONFIG —————
BASE_DIR = Path.home() / "PharmAlchemy_Project"
ONT_DIR  = BASE_DIR / "ontology"
DATA_DIR = BASE_DIR / "data"
APEX_DIR = BASE_DIR / "apex_upload"
APEX_DIR.mkdir(exist_ok=True)

HDO_FILE      = ONT_DIR  / "HumanDO_ontology_mapped.csv"
R_INPUT       = DATA_DIR / "disgenet_disease_mapped.csv"
D2R_INPUT     = DATA_DIR / "d2r_disgenet.csv"
R_OUTPUT      = DATA_DIR / "disgenet_disease_mapped_DO.csv"
D2R_OUTPUT    = DATA_DIR / "d2r_disgenet_DO.csv"
R_APEX_OUTPUT = APEX_DIR / "R_DISGENET_DISEASE_DO.csv"
D2R_APEX_OUT  = APEX_DIR / "D2R_DISGENET_DO.csv"

# ————— LOAD HDO MAPPINGS —————
hdo = pd.read_csv(HDO_FILE, dtype=str)
# Build map: lower-cased Label → DOID
hdo['label_lc'] = hdo['LABEL'].str.lower()
label_to_doid = dict(zip(hdo['label_lc'], hdo['DOID']))

# Function to map DOID by matching a column to HDO LABEL
def map_doid(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df[col] = df[col].astype(str)
    df['doid'] = df[col].str.lower().map(label_to_doid)
    return df

# ————— MAP for disgenet_disease_mapped.csv —————
r_df = pd.read_csv(R_INPUT, dtype=str)
r_df = map_doid(r_df, 'disease_name')
# Reorder columns for clarity
cols_r = ['umls_cui', 'mesh_id', 'mesh_label', 'disease_name', 'disease_type', 'disease_class', 'doid']
r_df = r_df[cols_r]
# Write outputs
r_df.to_csv(R_OUTPUT, index=False)
r_df.to_csv(R_APEX_OUTPUT, index=False)
print(f"[R] Wrote DOID-mapped diseases: {R_OUTPUT.name} ({len(r_df)} rows)")

# ————— MAP for d2r_disgenet.csv —————
d2r_df = pd.read_csv(D2R_INPUT, dtype=str)
d2r_df = map_doid(d2r_df, 'concept_name')
# Reorder columns
cols_d2r = ['drugbank_id', 'drugbank_name', 'umls_cui', 'mesh_id', 'mesh_label', 'concept_name', 'doid']
d2r_df = d2r_df[cols_d2r]
# Write outputs
d2r_df.to_csv(D2R_OUTPUT, index=False)
d2r_df.to_csv(D2R_APEX_OUT, index=False)
print(f"[D2R] Wrote DOID-mapped indications: {D2R_OUTPUT.name} ({len(d2r_df)} rows)")

