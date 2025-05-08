import pandas as pd
from pathlib import Path

# Load the raw STRING_G2G.csv
src = Path.home() / "PharmAlchemy_Project" / "data" / "STRING_G2G.csv"
df = pd.read_csv(src, dtype=str)

# Drop unnamed column if it exists
if "" in df.columns:
    df = df.drop(columns=[""])

# Rename for clarity
df = df.rename(columns={
    "UNIPROT_ID_1": "uniprot_id_1",
    "UNIPROT_ID_2": "uniprot_id_2",
    "gene_1": "gene_symbol_1",
    "gene_2": "gene_symbol_2"
})

# Extract gene_symbol and uniprot_id for both partners
df1 = df[["gene_symbol_1", "uniprot_id_1"]].rename(
    columns={"gene_symbol_1": "gene_symbol", "uniprot_id_1": "uniprot_id"}
)
df2 = df[["gene_symbol_2", "uniprot_id_2"]].rename(
    columns={"gene_symbol_2": "gene_symbol", "uniprot_id_2": "uniprot_id"}
)

# Combine both sides
genes = pd.concat([df1, df2], ignore_index=True)

# Clean: remove NA, remove duplicates
genes = genes.dropna().drop_duplicates()

# Clean gene_symbol: take only first token if multiple words, make uppercase
genes["gene_symbol"] = genes["gene_symbol"].apply(lambda x: x.split()[0].upper())

# Final columns: gene_symbol, uniprot_id
genes = genes[["gene_symbol", "uniprot_id"]]

# Save back to PharmAlchemy project
data_path = Path.home() / "PharmAlchemy_Project" / "data" / "G_STRING.csv"
apex_path = Path.home() / "PharmAlchemy_Project" / "apex_upload" / "G_STRING.csv"

genes.to_csv(data_path, index=False)
genes.to_csv(apex_path, index=False)

print(f"✅ Successfully cleaned G_STRING.csv with {len(genes)} rows!")

