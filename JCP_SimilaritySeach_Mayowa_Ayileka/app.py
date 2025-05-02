# --- FIXED app.py ---

import streamlit as st
import pandas as pd
from pymilvus import connections, Collection
from Search import run_vector_search
from Export import export_results_with_metadata
from Plot import get_projection_figure

# Connect to Milvus
connections.connect("default", host="localhost", port="19530")

st.title("JCP Vector Search ")

# Initialize session state for folders and selections
if "folders" not in st.session_state:
    st.session_state.folders = {}
if "folder_names" not in st.session_state:
    st.session_state.folder_names = []
if "selection_tracker" not in st.session_state:
    st.session_state.selection_tracker = {}

# Dataset selection
selected_dataset = st.sidebar.selectbox("Choose dataset(s) to search", options=["ORF", "CRISPR"])

@st.cache_data
def load_parquet(dataset):
    path = f"/Users/user/Desktop/INFO 602/JCP/Matches/{dataset}_Matches_enriched_with_meta.parquet"
    return pd.read_parquet(path)

df = load_parquet(selected_dataset)
gene_names = sorted(df["name"].dropna().unique().tolist())

# Sidebar: Folder creation
st.sidebar.markdown("---")
st.sidebar.markdown("### Folder Manager")
new_folder_name = st.sidebar.text_input("Create new folder", key="new_folder_input")
if st.sidebar.button("➕ Add Folder"):
    if new_folder_name and new_folder_name not in st.session_state.folders:
        st.session_state.folders[new_folder_name] = set()
        st.session_state.folder_names.append(new_folder_name)
        st.sidebar.success(f"Created folder: {new_folder_name}")

# Search bar
search_term = st.sidebar.text_input("🔍 Search gene name", value="", placeholder="Type gene name...")
if search_term:
    filtered = [name for name in gene_names if name.lower().startswith(search_term.lower())]
    selected_gene = st.sidebar.selectbox("Select a perturbation", filtered) if filtered else gene_names[0]
else:
    selected_gene = st.sidebar.selectbox("Select a perturbation", gene_names)

# Metadata preview
preview_row = df[df["name"] == selected_gene].iloc[0]
st.sidebar.markdown(f"### JCP Metadata for **{selected_gene}**")
for label, field in zip(["Source", "Plate", "Well", "JCP ID"],
                        ["Metadata_Source", "Metadata_Plate", "Metadata_Well", "Metadata_JCP2022"]):
    st.sidebar.markdown(f"**{label}:** {preview_row[field]}")

ensembl_id = preview_row.get("ensembl_id")
description = preview_row.get("description")
external_url = preview_row.get("external_url")

if ensembl_id:
    st.sidebar.markdown(f"**Ensembl ID:** {ensembl_id}")
if description:
    st.sidebar.markdown(f"**Description:** {description}")
if external_url:
    st.sidebar.markdown(f"[🔗 View on Ensembl]({external_url})", unsafe_allow_html=True)

embedding_cols = [col for col in df.columns if col.startswith("X_")]
query_vector = preview_row[embedding_cols].tolist()

metadata_options = ["name", "pert_type", "Metadata_JCP2022", "Metadata_Source", "Metadata_Plate", "Metadata_Well"]
pretty_labels = {
    "name": "Gene Name", "pert_type": "Perturbation Type", "Metadata_JCP2022": "JCP ID",
    "Metadata_Source": "Source", "Metadata_Plate": "Plate", "Metadata_Well": "Well"
}
metadata_cols = st.multiselect(
    "Metadata fields to include in the results",
    options=metadata_options,
    default=["name", "pert_type", "Metadata_JCP2022"],
    format_func=lambda x: pretty_labels.get(x, x)
)

k_neighbors = st.sidebar.number_input("Number of nearest neighbors to return (k)", 1, 50, 5)

if st.button("Run Vector Search"):
    collection = Collection(f"{selected_dataset.lower()}_embeddings")
    collection.load()

    matches = df[df["name"] == selected_gene]
    if matches.empty:
        st.warning(f" Gene '{selected_gene}' not found in dataset. Skipping.")
    else:
        query_row = matches.iloc[0]
        query_vector = query_row[embedding_cols].tolist()

        results = run_vector_search(
            collection=collection,
            query_vector=query_vector,
            k=k_neighbors + 1,
            output_fields=metadata_cols
        )

        result_rows = []
        seen = set()
        for hit in results[0]:
            meta = hit.entity
            unique_id = (meta.get("Metadata_JCP2022"), meta.get("name"))
            if meta and unique_id not in seen:
                seen.add(unique_id)
                result_rows.append({
                    "distance": float(hit.distance),
                    "Dataset": selected_dataset,
                    **{col: getattr(meta, col, None) for col in metadata_cols}
                })

        result_df = pd.DataFrame(result_rows)
        result_df = result_df[result_df["distance"] != 0].sort_values(by="distance").head(k_neighbors)
        display_df = result_df.rename(columns=pretty_labels).reset_index(drop=True)
        display_df.index += 1

        # Add checkbox column first
        display_df.insert(0, "Add to Folder", False)

        selected_folder = st.selectbox("📁 Choose folder to save genes from table", options=["None"] + st.session_state.folder_names, key="folder_table_select")
        edited_df = st.data_editor(display_df, use_container_width=True, num_rows="fixed")

        if selected_folder != "None":
            for _, row in edited_df.iterrows():
                if row["Add to Folder"]:
                    gene_id = row["JCP ID"]
                    gene_name = row["Gene Name"]
                    st.session_state.folders[selected_folder].add((gene_id, gene_name))
            st.success(f"Saved selected genes to '{selected_folder}'")

        st.download_button("Download CSV", result_df.to_csv(index=False), file_name="results.csv")
        st.download_button("Download JSON", result_df.to_json(orient="records", indent=2), file_name="results.json")

        st.markdown("---")
        show_plot = st.checkbox("Show 2D Plot of All Embeddings", value=True, key="show_plot_checkbox")

        if show_plot:
            method = ""
            top_hit_ids = result_df["Metadata_JCP2022"].tolist()
            query_id = preview_row["Metadata_JCP2022"]

            output = get_projection_figure(query_id=query_id, top_k_ids=top_hit_ids, method=method)
            if output and output[0] is not None:
                fig, proj_df, _ = output
                focus_points = proj_df[proj_df["Highlight"].isin(["Query", "Top Match"])]
                padding_ratio = 0.15
                min_x, max_x = focus_points["X1"].min(), focus_points["X1"].max()
                min_y, max_y = focus_points["X2"].min(), focus_points["X2"].max()
                pad_x = (max_x - min_x) * padding_ratio if max_x > min_x else 1
                pad_y = (max_y - min_y) * padding_ratio if max_y > min_y else 1
                fig.update_xaxes(range=[min_x - pad_x, max_x + pad_x])
                fig.update_yaxes(range=[min_y - pad_y, max_y + pad_y], scaleanchor="x")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"{method} projection failed. Try PCA or check data integrity.")

# --- View folders ---
# if st.sidebar.checkbox("📁 View Folders"):
#     st.subheader("📁 Saved Folders")
#     if not st.session_state.folders:
#         st.info("No folders created yet.")
#     else:
#         folders_to_delete = []
#         for folder_name, gene_keys in st.session_state.folders.items():
#             st.markdown(f"### 📂 {folder_name}")
#             folder_df = pd.DataFrame(list(gene_keys), columns=["Metadata_JCP2022", "name"])
#             merged = pd.merge(folder_df, df, on=["Metadata_JCP2022", "name"], how="left")

#             if merged.empty:
#                 st.warning("No matching genes found.")
#                 continue

#             genes_to_remove = []
#             for _, row in merged.iterrows():
#                 st.markdown(f"**{row['name']} ({row['Metadata_JCP2022']})**")
#                 st.markdown(f"• Source: {row['Metadata_Source']}")
#                 st.markdown(f"• Plate: {row['Metadata_Plate']}")
#                 st.markdown(f"• Well: {row['Metadata_Well']}")
#                 st.markdown(f"• Perturbation Type: {row['pert_type']}")
#                 if row.get("ensembl_id"):
#                     st.markdown(f"• Ensembl ID: {row['ensembl_id']}")
#                 if row.get("description"):
#                     st.markdown(f"• Description: {row['description']}")
#                 if row.get("external_url"):
#                     st.markdown(f"[🔗 View on Ensembl]({row['external_url']})", unsafe_allow_html=True)
#                 if st.button(f" Remove {row['name']}", key=f"remove_{folder_name}_{row['Metadata_JCP2022']}"):
#                     genes_to_remove.append((row['Metadata_JCP2022'], row['name']))
#                 st.markdown("---")
#             for gene_key in genes_to_remove:
#                 st.session_state.folders[folder_name].discard(gene_key)

#             if st.button(f"🗑️ Delete Folder '{folder_name}'", key=f"delete_{folder_name}"):
#                 folders_to_delete.append(folder_name)

#         for folder in folders_to_delete:
#             del st.session_state.folders[folder]
#             st.session_state.folder_names.remove(folder)
#             st.success(f"Deleted folder: {folder}")
