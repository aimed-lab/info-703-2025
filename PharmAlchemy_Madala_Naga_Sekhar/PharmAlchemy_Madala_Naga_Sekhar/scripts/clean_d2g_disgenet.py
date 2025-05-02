#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

# ————— CONFIG —————
BASE = Path.home() / "PharmAlchemy_Project"
RAW  = BASE / "data" / "DisGeNET" / "DisGeNet_D2G.csv"
OUT  = BASE / "data" / "g2d_disgenet.csv"

# ———— LOAD ————
df = pd.read_csv(RAW, dtype=str)
print("Columns found:", df.columns.tolist())

# — Drop the unnamed first column if it exists — 
if "" in df.columns:
    df = df.drop(columns=[""])

# — Rename to lowercase, consistent names —
df = df.rename(columns={
    "gene": "gene_symbol",
    "UMLS": "umls_cui"
})

# — Drop rows missing either gene or disease ID —
df = df.dropna(subset=["gene_symbol", "umls_cui"])
print(f"Rows after dropping nulls: {len(df)}")

# — Keep only the key columns —
df = df[["gene_symbol", "umls_cui"]]

# — Write out —
df.to_csv(OUT, index=False)
print(f"Wrote cleaned file: {OUT} ({len(df)} rows)")

