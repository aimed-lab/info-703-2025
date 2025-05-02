import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.decomposition import PCA
from umap import UMAP

def get_projection_figure(method="PCA", query_id=None, top_k_ids=None):
    # Function to create 2D PCA plots

    # Load datasets
    orf_df = pd.read_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/ORF_Matches_enriched.parquet")
    crispr_df = pd.read_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/CRISPR_Matches_enriched.parquet")

    # Add dataset label
    orf_df["Dataset"] = "ORF"
    crispr_df["Dataset"] = "CRISPR"

    # Identify common embedding columns
    orf_embed_cols = [col for col in orf_df.columns if col.startswith("X_")]
    crispr_embed_cols = [col for col in crispr_df.columns if col.startswith("X_")]
    common_embed_cols = list(set(orf_embed_cols).intersection(crispr_embed_cols))

    # Prepare embeddings and metadata
    orf_embeddings = orf_df[common_embed_cols].astype(np.float32)
    crispr_embeddings = crispr_df[common_embed_cols].astype(np.float32)
    all_embeddings = pd.concat([orf_embeddings, crispr_embeddings], ignore_index=True)
    all_meta = pd.concat([orf_df, crispr_df], ignore_index=True)

    # Clean embeddings
    all_embeddings.replace([np.inf, -np.inf], np.nan, inplace=True)
    valid_idx = all_embeddings.dropna().index
    clean_embeddings = all_embeddings.loc[valid_idx].reset_index(drop=True)
    clean_meta = all_meta.loc[valid_idx].reset_index(drop=True)

    # Remove all-zero rows
    non_zero_mask = ~(clean_embeddings.sum(axis=1) == 0)
    clean_embeddings = clean_embeddings.loc[non_zero_mask].reset_index(drop=True)
    clean_meta = clean_meta.loc[non_zero_mask].reset_index(drop=True)

    # Run dimensionality reduction
    try:
        reducer = PCA(n_components=2)

        X_proj = reducer.fit_transform(clean_embeddings)

        if not np.isfinite(X_proj).all():
            raise ValueError("Projection output contains non-finite values.")

    except Exception as e:
        print(f" Error during {method} projection: {e}")
        return None, pd.DataFrame(), None

    # Store projection coordinates
    clean_meta["X1"] = X_proj[:, 0]
    clean_meta["X2"] = X_proj[:, 1]

    # Label highlights
    clean_meta["Highlight"] = "Other"
    if query_id:
        query_match = clean_meta[clean_meta["Metadata_JCP2022"] == query_id].head(1).index
        clean_meta.loc[query_match, "Highlight"] = "Query"
    if top_k_ids:
        for top_id in top_k_ids:
            row_idx = clean_meta[clean_meta["Metadata_JCP2022"] == top_id].head(1).index
            if len(row_idx) > 0:
                clean_meta.loc[row_idx, "Highlight"] = "Top Match"

    # Plot
    color_map = {"Query": "red", "Top Match": "orange", "Other": "lightblue"}
    fig = px.scatter(
        clean_meta,
        x="X1", y="X2",
        color="Highlight",
        color_discrete_map=color_map,
        hover_data=["name", "Metadata_JCP2022", "pert_type"],
        title=f"2D {method} of ORF and CRISPR Embeddings"
    )
    fig.update_traces(marker=dict(size=5))

    return fig, clean_meta, query_id