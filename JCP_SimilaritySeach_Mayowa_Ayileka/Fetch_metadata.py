import pandas as pd
import requests
import time

# Load gene names from ORF dataset
df = pd.read_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/ORF_Matches_enriched.parquet")
gene_names = sorted(df["name"].dropna().unique())
print(f"Found {len(gene_names)} unique gene names.")

# Ensembl batch lookup endpoint
ENSEMBL_BATCH_URL = "https://rest.ensembl.org/lookup/symbol/homo_sapiens"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

def fetch_batch(gene_list):
    payload = {"symbols": gene_list}
    try:
        response = requests.post(ENSEMBL_BATCH_URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            data = response.json()
            return [
                {
                    "name": gene,
                    "ensembl_id": data[gene].get("id") if gene in data else None,
                    "description": data[gene].get("description") if gene in data else None,
                    "biotype": data[gene].get("biotype") if gene in data else None,
                    "species": data[gene].get("species") if gene in data else None,
                    "external_url": f"https://www.ensembl.org/id/{data[gene].get('id')}" if gene in data and data[gene].get("id") else None
                }
                for gene in gene_list
            ]
        else:
            print(f" Request failed with status code {response.status_code}")
            return [{"name": gene} for gene in gene_list]
    except Exception as e:
        print(f" Error: {e}")
        return [{"name": gene} for gene in gene_list]

# Split into batches of up to 1000
BATCH_SIZE = 1000
all_metadata = []
for i in range(0, len(gene_names), BATCH_SIZE):
    batch = gene_names[i:i + BATCH_SIZE]
    print(f" Fetching batch {i}–{i + len(batch)}")
    result = fetch_batch(batch)
    all_metadata.extend(result)
    time.sleep(0.3)  # polite delay between batches

# Save metadata
meta_df = pd.DataFrame(all_metadata)
meta_df.to_csv("/Users/user/Desktop/gene_annotations.csv", index=False)
print(" Done: saved metadata to gene_annotations.csv")