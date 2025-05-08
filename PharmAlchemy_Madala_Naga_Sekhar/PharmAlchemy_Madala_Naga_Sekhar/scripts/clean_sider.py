import pandas as pd
from pathlib import Path

# Paths
BASE = Path.home() / "PharmAlchemy_Project"
DATA_DIR = BASE / "data"
ONTO_DIR = BASE / "ontology"
APEX_DIR = BASE / "apex_upload"
APEX_DIR.mkdir(exist_ok=True)

# Load SIDER Side Effects
sider = pd.read_csv(DATA_DIR / "SIDER_Side_Effects.csv", dtype=str)

# Load Ontology mappings
mesh_umls = pd.read_csv(ONTO_DIR / "mesh_umls_mapping.csv", dtype=str)
mesh_terms = pd.read_csv(ONTO_DIR / "mesh_terms.csv", dtype=str)

# Merge to get MeSH ID
merged = sider.merge(
    mesh_umls, left_on="UMLS_CUI_From_Meddra", right_on="umls_code", how="left"
)

# Merge to get MeSH label
merged = merged.merge(
    mesh_terms, left_on="mesh_code", right_on="DescriptorUI", how="left"
)

# Final columns
merged_final = merged.rename(columns={
    "DrugBank_ID": "drugbank_id",
    "DrugBank_Name": "drugbank_name",
    "UMLS_CUI_From_Meddra": "umls_cui",
    "PreferredTerm": "mesh_label"
})[[
    "drugbank_id", "drugbank_name", "umls_cui", "mesh_code", "mesh_label", "Side_Effect"
]]

# Save outputs
out_csv = DATA_DIR / "d2ae_sider.csv"
apex_csv = APEX_DIR / "d2ae_sider.csv"
merged_final.to_csv(out_csv, index=False)
merged_final.to_csv(apex_csv, index=False)

print(f"✅ d2ae_sider.csv created successfully with {len(merged_final)} rows!")

