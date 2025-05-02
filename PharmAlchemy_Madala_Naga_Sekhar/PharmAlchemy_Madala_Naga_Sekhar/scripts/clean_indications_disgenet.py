#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

# ————— CONFIG —————
BASE       = Path.home() / "PharmAlchemy_Project"
RAW        = BASE / "data" / "DisGeNET" / "DisGeNet_Indications.csv"
CROSSWALK  = BASE / "ontology" / "mesh_umls_mapping.csv"
DESCRIPT   = BASE / "ontology" / "mesh_terms.csv"
OUT        = BASE / "data" / "d2r_disgenet.csv"

# ———— LOAD RAW ————
df = pd.read_csv(RAW, dtype=str)
print(f"Loaded {len(df)} rows from {RAW.name}")

# — Drop any unnamed index col —
if "Unnamed: 0" in df.columns:
    df = df.drop(columns=["Unnamed: 0"])

# — Normalize column names —
df.columns = [c.strip() for c in df.columns]

# — Keep & rename key cols —
#   DrugBank_ID, DrugBank_Name, UMLS_CUI_From_Label, Concept_Name
df = df[["DrugBank_ID", "DrugBank_Name", 
         "UMLS_CUI_From_Label", "Concept_Name"]]
df = df.rename(columns={
    "DrugBank_ID": "drugbank_id",
    "DrugBank_Name": "drugbank_name",
    "UMLS_CUI_From_Label": "umls_cui",
    "Concept_Name": "concept_name"
})

# — Drop rows missing critical IDs —
df = df.dropna(subset=["drugbank_id", "umls_cui"])
print(f"After dropping nulls: {len(df)} rows")

# — Map UMLS → MeSH_ID —
cross = pd.read_csv(CROSSWALK, dtype=str)
cross = cross.rename(columns={
    "umls_code": "umls_cui",
    "mesh_code": "mesh_id"
})
df = df.merge(cross, on="umls_cui", how="left")

# — Map MeSH_ID → MeSH_Label —
terms = pd.read_csv(DESCRIPT, dtype=str)
terms = terms.rename(columns={
    "DescriptorUI": "mesh_id",
    "PreferredTerm": "mesh_label"
})
df = df.merge(terms[["mesh_id", "mesh_label"]], on="mesh_id", how="left")

# — Final reorder & write —
final_cols = [
    "drugbank_id",
    "drugbank_name",
    "umls_cui",
    "mesh_id",
    "mesh_label",
    "concept_name"
]
df[final_cols].to_csv(OUT, index=False)
print(f"Wrote mapped file: {OUT} ({len(df)} rows)")

