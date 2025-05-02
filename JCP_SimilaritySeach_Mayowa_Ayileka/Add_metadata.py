import pandas as pd

# Load metadata
meta_df = pd.read_csv("/Users/user/Desktop/gene_annotations.csv")

# Merge with ORF
orf_df = pd.read_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/ORF_Matches_enriched.parquet")
orf_merged = orf_df.merge(meta_df, on="name", how="left")
orf_merged.to_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/ORF_Matches_enriched_with_meta.parquet", index=False)

# Merge with CRISPR
crispr_df = pd.read_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/CRISPR_Matches_enriched.parquet")
crispr_merged = crispr_df.merge(meta_df, on="name", how="left")
crispr_merged.to_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/CRISPR_Matches_enriched_with_meta.parquet", index=False)

print("Both ORF and CRISPR datasets updated with gene metadata.")