#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

# --- CONFIGURE PATHS ---
BASE     = Path.home() / "PharmAlchemy_Project"
RAW      = BASE / "data" / "DisGeNET" / "DisGeNet_disease_final.csv"
ONTO     = BASE / "ontology"
OUT_CSV  = BASE / "data" / "disgenet_disease_mapped.csv"

# ✅ Updated ontology filenames
CROSSWALK = ONTO / "mesh_umls_mapping.csv"  # columns: umls_code, mesh_code
DESCRIPT  = ONTO / "mesh_terms.csv"         # columns: DescriptorUI, PreferredTerm

# --- 1. LOAD RAW DATA ---
df = pd.read_csv(RAW, dtype=str)
print(f"Raw rows: {len(df)}")

# --- 2. CLEAN & NORMALIZE ---
keep = ["UMLS_CUI", "Disease_Name", "Disease_Type", "Disease_Class"]
df = df[keep].dropna(subset=["UMLS_CUI", "Disease_Name"])
df.columns = [c.lower() for c in df.columns]
df["umls_cui"] = df["umls_cui"].str.strip()
print(f"After dropna: {len(df)}")

# --- 3. MAP UMLS → MeSH ---
cross = pd.read_csv(CROSSWALK, dtype=str)
cross.columns = [c.lower() for c in cross.columns]
cross = cross.rename(columns={"umls_code": "umls_cui", "mesh_code": "mesh_id"})
df = df.merge(cross, on="umls_cui", how="left")

# --- 4. MAP MeSH → PreferredTerm (label) ---
terms = pd.read_csv(DESCRIPT, dtype=str)
terms = terms.rename(columns={"DescriptorUI": "mesh_id", "PreferredTerm": "mesh_label"})
terms["mesh_id"] = terms["mesh_id"].str.strip()
df = df.merge(terms[["mesh_id", "mesh_label"]], on="mesh_id", how="left")

# --- 5. FINALIZE ---
final_cols = [
    "umls_cui",
    "mesh_id",
    "mesh_label",
    "disease_name",
    "disease_type",
    "disease_class"
]
df = df[final_cols]
df.to_csv(OUT_CSV, index=False)
print(f"✅ Mapped file written to: {OUT_CSV} ({len(df)} rows)")

