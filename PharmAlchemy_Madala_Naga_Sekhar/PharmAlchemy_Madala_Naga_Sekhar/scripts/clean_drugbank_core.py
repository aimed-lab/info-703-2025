#!/usr/bin/env python3
import pandas as pd
import re
from pathlib import Path

# ————— CONFIG —————
BASE       = Path.home() / "PharmAlchemy_Project"
DATA       = BASE / "data" / "DrugBank"
ONTO_PR    = BASE / "ontology" / "PR.csv"

# Core input
FILE_DRUGMAP = DATA / "DrugBank_ID_Drug_Mappings.csv"
FILE_UPLINK  = DATA / "DrugBank Drug-Target UniProt Links.csv"

# Outputs
OUT_D   = BASE / "data" / "d_drugbank.csv"
OUT_D2G = BASE / "data" / "d2g_drugbank.csv"

# ——— 1. Load drug metadata ———
df_drugs = pd.read_csv(FILE_DRUGMAP, dtype=str)
df_drugs = df_drugs.rename(columns={
    df_drugs.columns[0]: "drugbank_id",
    df_drugs.columns[1]: "drug_name"
})[["drugbank_id", "drug_name"]].dropna()
print(f"[D] Loaded {len(df_drugs)} drugs")

# ——— 2. Write D table ———
df_drugs.to_csv(OUT_D, index=False)
print(f"[D] Written → {OUT_D}")

# ——— 3. Load Drug→UniProt links ———
df_links = pd.read_csv(FILE_UPLINK, dtype=str)
df_links.columns = [c.strip() for c in df_links.columns]
df_links = df_links.rename(columns={
    "DrugBank ID": "drugbank_id",
    "UniProt_ID": "uniprot_id"
})[["drugbank_id", "uniprot_id"]].dropna()
print(f"[D2G] Loaded {len(df_links)} drug→UniProt links")

# ——— 4. Merge drug names ———
df_d2g = df_links.merge(df_drugs, on="drugbank_id", how="left")

# ——— 5. Build UniProt → PR mapping ———
pr_map = {}
if ONTO_PR.exists():
    pr_df = pd.read_csv(ONTO_PR, dtype=str)
    for _, row in pr_df.iterrows():
        pro_id = row["Class ID"].strip()
        xrefs = row.get("database_cross_reference", "")
        if pd.isna(xrefs): 
            continue
        # split on common delimiters, look for UniProtKB:
        for part in re.split(r"[|;,\s]+", xrefs):
            if part.startswith("UniProtKB:"):
                up_acc = part.split(":",1)[1]
                pr_map[up_acc] = pro_id
    print(f"[D2G] Built PR mapping for {len(pr_map)} UniProt IDs")
else:
    print("[D2G] PR ontology file not found, skipping PR mapping")

# ——— 6. Apply PR mapping ———
df_d2g["pr_id"] = df_d2g["uniprot_id"].map(pr_map)

# ——— 7. Finalize & write D2G ———
df_d2g = df_d2g[["drugbank_id", "drug_name", "uniprot_id", "pr_id"]].drop_duplicates()
df_d2g.to_csv(OUT_D2G, index=False)
print(f"[D2G] Written → {OUT_D2G} ({len(df_d2g)} rows)")

