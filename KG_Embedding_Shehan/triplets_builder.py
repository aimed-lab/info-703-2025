"""
Module to build RDF-style triplets from filtered datasets (R2G_validated, R2D_filtered, D2G_filtered, G2G_filtered)
and concatenate them into a single DataFrame of triplets, plus compute unique entities and predicates.
Function:
    build_triplets(r2g_csv, r2d_csv, d2g_csv, g2g_csv, output_dir)

This will write `triplets_R2G.csv`, `triplets_R2D.csv`, `triplets_D2G.csv`, `triplets_G2G.csv`,
and `all_triplets.csv` to the output directory, and return the combined DataFrame along with
sets of unique entities and predicates.
"""
import os
import pandas as pd
import numpy as np


def build_triplets(r2g_csv, r2d_csv, d2g_csv, g2g_csv, output_dir):
    """
    Reads the four filtered CSV files, builds triplets for each, and saves them and a merged file.

    Parameters:
    - r2g_csv: path to R2G_validated.csv
    - r2d_csv: path to R2D_filtered.csv
    - d2g_csv: path to D2G_filtered.csv
    - g2g_csv: path to G2G_filtered.csv
    - output_dir: directory where the triplet CSVs will be saved

    Returns:
    - all_triplets: pandas.DataFrame of merged triplets (columns: ['subject', 'predicate', 'object'])
    - unique_entities: set of all distinct subjects and objects
    - unique_predicates: set of all distinct predicates
    """
    # Ensure output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    R2G = pd.read_csv(r2g_csv)
    R2D = pd.read_csv(r2d_csv)
    D2G = pd.read_csv(d2g_csv)
    G2G = pd.read_csv(g2g_csv)

    # Triplets for R2G_validated
    df = R2G.copy()
    df['interaction_types'] = df['interaction_types'].astype(str).replace({'nan': ''})
    rows = []
    for _, row in df.iterrows():
        drug = row['drug_name']
        gene = row['gene_name']
        types = row['interaction_types']
        if types.strip() == '':
            rows.append((drug, 'drug/interacts_with/gene', gene))
        else:
            for t in types.split(','):
                t_clean = t.strip().strip("'").strip()
                if t_clean:
                    rel = f'drug/interacts_with/{t_clean}/gene'
                    rows.append((drug, rel, gene))
    triplets_R2G = pd.DataFrame(rows, columns=['head','relation','tail']).drop_duplicates().reset_index(drop=True)
    triplets_R2G['relation'] = triplets_R2G['relation'].str.replace(r'/<NA>$', '', regex=True).str.rstrip('/')
    triplets_R2G.to_csv(os.path.join(output_dir, 'triplets_R2G.csv'), index=False)

    # Triplets for R2D_filtered 
    df = R2D.copy()
    
    for col in ['DRUGBANK_NAME_DISGENET', 'INDICATION', 'SIDE_EFFECT', 'PHENOTYPE']:
        df[col] = df[col].astype(str).str.upper().replace('NAN', np.nan)
    df = df[df['DRUGBANK_NAME_DISGENET'].notna()]
    rows = []
    for _, row in df.iterrows():
        drug = row['DRUGBANK_NAME_DISGENET']
        phen = row['PHENOTYPE']
        if phen in ['INDICATIONS', 'BOTH']:
            if pd.notna(row['INDICATION']):
                rows.append((drug, 'drug/treats/disease', row['INDICATION']))
        if phen in ['SIDE EFFECT', 'BOTH']:
            if pd.notna(row['SIDE_EFFECT']):
                rows.append((drug, 'drug/has_side_effect/side_effect', row['SIDE_EFFECT']))
    triplets_R2D = pd.DataFrame(rows, columns=['head','relation','tail']).drop_duplicates().reset_index(drop=True)
    triplets_R2D.to_csv(os.path.join(output_dir, 'triplets_R2D.csv'), index=False)

    # Triplets for D2G_filtered 
    df = D2G.copy()
    
    df['GENE_SYMBOL'] = df['GENE_SYMBOL'].astype(str).str.upper().str.strip()
    df['DISEASE_NAME'] = df['DISEASE_NAME'].astype(str).str.upper().str.strip()
    df['DISEASE_SEMANTIC_TYPE'] = df['DISEASE_SEMANTIC_TYPE'].astype(str).str.upper().str.strip()
    df['DISEASE_CLASS'] = df['DISEASE_CLASS'].fillna('').astype(str).str.upper().str.strip()
    df['DSI'] = pd.to_numeric(df['DSI'], errors='coerce')
    df['DPI'] = pd.to_numeric(df['DPI'], errors='coerce')

    bins = [-float('inf'), 0.33, 0.66, float('inf')]
    dsi_labels = ['DSI_LOW','DSI_MEDIUM','DSI_HIGH']
    dpi_labels = ['DPI_LOW','DPI_MEDIUM','DPI_HIGH']
    df['DSI_CATEGORY'] = pd.cut(df['DSI'], bins=bins, labels=dsi_labels)
    df['DPI_CATEGORY'] = pd.cut(df['DPI'], bins=bins, labels=dpi_labels)

    rows = []
    for _, row in df.iterrows():
        gene    = row['GENE_SYMBOL']
        disease = row['DISEASE_NAME']
        semantic = row['DISEASE_SEMANTIC_TYPE']
        classes = row['DISEASE_CLASS'].split(';') if row['DISEASE_CLASS'] else []
        if pd.notna(gene) and pd.notna(disease) and semantic and semantic != 'NAN':
            rel = f"gene/associated_with/{semantic.replace(' ', '_')}/disease"
            rows.append((gene, rel, disease))
        for cls in classes:
            cls = cls.strip().lower()
            if cls:
                rows.append((disease, 'disease/has_class/disease_class', cls))
    triplets_D2G = pd.DataFrame(rows, columns=['head','relation','tail']).drop_duplicates().reset_index(drop=True)
    triplets_D2G.to_csv(os.path.join(output_dir, 'triplets_D2G.csv'), index=False)

    # Triplets for G2G_filtered
    df = G2G.copy()
    df['GENE_NAMES_1'] = df['GENE_NAMES_1'].astype(str).str.upper().str.strip()
    df['GENE_NAMES_2'] = df['GENE_NAMES_2'].astype(str).str.upper().str.strip()
    rows = []
    for _, row in df.iterrows():
        head = row['GENE_NAMES_1']
        tail = row['GENE_NAMES_2']
        if head and tail:
            rows.append((head, 'gene/associated_with/gene', tail))
    triplets_G2G = pd.DataFrame(rows, columns=['head','relation','tail']).drop_duplicates().reset_index(drop=True)
    triplets_G2G.to_csv(os.path.join(output_dir, 'triplets_G2G.csv'), index=False)

    # Merge all triplets
    all_triplets = pd.concat([
        triplets_R2G, triplets_R2D, triplets_D2G, triplets_G2G
    ], ignore_index=True).drop_duplicates().reset_index(drop=True)
    all_triplets = all_triplets.dropna(subset=['head','tail'])
    all_triplets = all_triplets.rename(columns={'head':'subject','relation':'predicate','tail':'object'})
    all_triplets.to_csv(os.path.join(output_dir, 'all_triplets.csv'), index=False)

    # Unique entities & predicates
    unique_entities = set(all_triplets['subject']).union(all_triplets['object'])
    unique_predicates = set(all_triplets['predicate'])

    print(f"Saved all_triplets.csv ({len(all_triplets)} rows)")
    print(f"Unique entities: {len(unique_entities)}, predicates: {len(unique_predicates)}")

    return all_triplets, unique_entities, unique_predicates


if __name__ == '__main__':
    # Interactive CLI
    r2g_csv = input("Path to R2G_validated.csv: ")
    r2d_csv = input("Path to R2D_filtered.csv: ")
    d2g_csv = input("Path to D2G_filtered.csv: ")
    g2g_csv = input("Path to G2G_filtered.csv: ")
    output_dir = input("Directory to save triplet files: ")

    build_triplets(r2g_csv, r2d_csv, d2g_csv, g2g_csv, output_dir)
