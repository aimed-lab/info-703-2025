#!/usr/bin/env python3
"""
Generate PharmAlchemy‑ready DrugBank interaction tables:
    • D2E  – Drug → Enzyme
    • D2T  – Drug → Transporter
    • D2C  – Drug → Carrier

For every archetype the script will:
1. Load the corresponding *Drug‑UniProt Links* file – the authoritative mapping of
   `DrugBank ID` → `UniProt_ID` for that interaction type.
2. Attach the human‑readable drug name from `DrugBank_ID_Drug_Mappings.csv`.
3. Optionally add the Protein Ontology (PR) identifier if `ontology/PR.csv` is present.
4. De‑duplicate, standardise column names, and write two copies of each result:
       • data/<archetype>.csv   – raw storage
       • apex_upload/<ARCTYPE>.csv – ready for Oracle APEX upload

Column layout (exactly matches PharmAlchemy spec):
    drugbank_id, drug_name, uniprot_id, pr_id

Notes
-----
* The legacy *Identifiers.csv* files are **not** required – the UniProt link file
  already contains the DrugBank IDs. Including the identifier file added no new
  rows and occasionally introduced duplicates, so we rely solely on the link
  files to keep things clean and fast.
* If `PR.csv` is not found the script still runs – the `pr_id` column is filled
  with blanks.
* Updated to extract PR ID and UniProt ID from full URLs and labels in `PR.csv`.
"""
from pathlib import Path
import pandas as pd

def load_drug_names(drug_file: Path) -> pd.DataFrame:
    df = pd.read_csv(drug_file, dtype=str)
    df = df.rename(columns={df.columns[0]: "drugbank_id", df.columns[1]: "drug_name"})
    return df[["drugbank_id", "drug_name"]].dropna()

def load_pr_mapping(pr_file: Path) -> pd.DataFrame:
    if not pr_file.exists():
        return pd.DataFrame(columns=["uniprot_id", "pr_id"])

    df = pd.read_csv(pr_file, dtype=str)

    # Extract PR ID from Class ID (e.g., PR:Q9JHD2 from .../obo/PR_Q9JHD2)
    df["pr_id"] = df["Class ID"].str.extract(r"(PR:[^\\s|,]+)", expand=False)

    # Extract UniProt ID from database_cross_reference (e.g., UniProtKB:Q9JHD2)
    def extract_uniprot(x):
        if pd.isna(x):
            return None
        for part in str(x).split('|'):
            if part.startswith("UniProtKB:"):
                return part.split(":")[1]
        return None

    df["uniprot_id"] = df["database_cross_reference"].apply(extract_uniprot)
    return df[["uniprot_id", "pr_id"]].dropna()

def build_table(archetype: str, link_file: Path, drug_df: pd.DataFrame,
                pr_df: pd.DataFrame, out_dir: Path, apex_dir: Path) -> None:
    if not link_file.exists():
        print(f"[WARN] {link_file.name} not found – skipping {archetype.upper()}.")
        return

    df = pd.read_csv(link_file, dtype=str)
    df = df.rename(columns={
        "DrugBank ID": "drugbank_id",
        "UniProt_ID": "uniprot_id",
        "UniProt ID": "uniprot_id",
    })
    if {"drugbank_id", "uniprot_id"}.issubset(df.columns) is False:
        print(f"[ERROR] Expected columns not found in {link_file.name}; columns are {list(df.columns)}")
        return

    df = df[["drugbank_id", "uniprot_id"]].dropna()
    df = df.merge(drug_df, on="drugbank_id", how="left")
    if not pr_df.empty:
        df = df.merge(pr_df, on="uniprot_id", how="left")
    else:
        df["pr_id"] = None

    df = df.drop_duplicates().sort_values(["drugbank_id", "uniprot_id"])

    std_out = out_dir / f"d2{archetype[0]}_drugbank.csv"
    apex_out = apex_dir / f"D2{archetype[0].upper()}_DRUGBANK.csv"

    df.to_csv(std_out, index=False)
    df.to_csv(apex_out, index=False)

    print(f"[{archetype.upper()}] {len(df):,} rows → {std_out.name} & {apex_out.name}")

def main():
    BASE = Path.home() / "PharmAlchemy_Project"
    data_dir = BASE / "data" / "DrugBank"
    out_dir = BASE / "data"
    apex_dir = BASE / "apex_upload"
    apex_dir.mkdir(exist_ok=True)

    drug_map_file = data_dir / "DrugBank_ID_Drug_Mappings.csv"
    pr_file = BASE / "ontology" / "PR.csv"

    drug_df = load_drug_names(drug_map_file)
    pr_df   = load_pr_mapping(pr_file)

    FILE_MAP = {
        "carrier": data_dir / "DrugBank Carrier Drug-UniProt Links.csv",
        "enzyme": data_dir / "DrugBank Drug-Enzyme UniProt Links.csv",
        "transporter": data_dir / "DrugBank Transporter Drug-UniProt Links.csv",
    }

    for archetype, link_path in FILE_MAP.items():
        build_table(archetype, link_path, drug_df, pr_df, out_dir, apex_dir)

if __name__ == "__main__":
    main()

