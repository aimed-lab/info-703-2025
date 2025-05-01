"""
Module to filter R2D, D2G, G2G datasets based on R2G_validated and save the filtered outputs.
Function:
    filter_and_save(r2d_path, r2g_validated_path, d2g_path, g2g_path, output_dir)

Reads the four CSVs, applies successive filters, and writes four filtered CSVs to output_dir.
"""
import os
import pandas as pd

def filter_and_save(r2d_path, r2g_validated_path, d2g_path, g2g_path, output_dir):
    # Load data
    R2D = pd.read_csv(r2d_path, index_col=False)
    R2G_validated = pd.read_csv(r2g_validated_path, index_col=False)
    D2G = pd.read_csv(d2g_path, index_col=False)
    G2G = pd.read_csv(g2g_path, index_col=False)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Filter R2D using R2G_validated
    R2G_validated['CID'] = pd.to_numeric(R2G_validated['CID'], errors='coerce').astype('Int64').astype(str)
    R2D['PUBCHEM_CID'] = pd.to_numeric(R2D['PUBCHEM_CID'], errors='coerce').astype('Int64').astype(str)

    valid_cids = set(R2G_validated['CID'].dropna().unique())
    R2D_filtered = R2D[R2D['PUBCHEM_CID'].isin(valid_cids)].reset_index(drop=True)

    # Filter D2G using R2D_filtered
    in_set = set(R2D_filtered['UMLS_CUI_FROM_LABEL'].dropna().unique())
    med_set = set(R2D_filtered['UMLS_CUI_FROM_MEDDRA'].dropna().unique())
    valid_umls = in_set.union(med_set)
    D2G_filtered = D2G[D2G['UMLS'].isin(valid_umls)].reset_index(drop=True)

    # Filter G2G using union of genes from D2G_filtered and R2G_validated ---
    genes_d2g = set(D2G_filtered['GENE_SYMBOL'].dropna().unique())
    genes_r2g = set(R2G_validated['gene_name'].dropna().unique())
    valid_genes = genes_d2g.union(genes_r2g)
    G2G_filtered = G2G[(G2G['GENE_NAMES_1'].isin(valid_genes)) |
                       (G2G['GENE_NAMES_2'].isin(valid_genes))].reset_index(drop=True)

    # Save outputs
    R2G_validated.to_csv(os.path.join(output_dir, 'R2G_validated.csv'), index=False)
    R2D_filtered.to_csv(os.path.join(output_dir, 'R2D_filtered.csv'), index=False)
    D2G_filtered.to_csv(os.path.join(output_dir, 'D2G_filtered.csv'), index=False)
    G2G_filtered.to_csv(os.path.join(output_dir, 'G2G_filtered.csv'), index=False)

    print(f"Filtered files saved in: {output_dir}")


if __name__ == '__main__':
    import getpass

    # Prompt user for file paths
    r2d_path            = input("Enter path to R2D CSV: ")
    r2g_validated_path  = input("Enter path to R2G_validated CSV: ")
    d2g_path            = input("Enter path to D2G CSV: ")
    g2g_path            = input("Enter path to G2G CSV: ")
    output_dir          = input("Enter directory to save filtered CSVs: ")

    filter_and_save(r2d_path,
                    r2g_validated_path,
                    d2g_path,
                    g2g_path,
                    output_dir)
