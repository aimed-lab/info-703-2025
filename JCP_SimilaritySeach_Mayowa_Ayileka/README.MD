# Jump Cell Painting: Vector Database and Embedding Integration

An interactive vector-based similarity search tool designed for exploring morphological profiles from the JUMP Cell Painting dataset. This platform enables researchers to perform fast, interpretable, and customizable searches across high-dimensional cell image embeddings.

---

##  Project Overview

This project bridges high-content cellular imaging data with modern vector search infrastructure to enable intuitive exploration of morphological similarity. Users can search across genetic perturbation datasets (ORF and CRISPR), visualize results with PCA or UMAP, and export findings for downstream analysis.

---

## Key Features

-  **Vector Similarity Search** across ORF and CRISPR datasets using Milvus
-  **Dimensionality Reduction** with PCA and UMAP (3D visualizations)
-  **Rich Metadata Integration** (plate, well, gene, perturbation type, etc.)
-  **CSV/JSON Export** of search results
-  **Interactive Streamlit UI** with customizable filters and dataset selection
-  **Modular Python Backend** for loading, searching, and plotting

---

##  Technologies Used

| Tool/Library   | Purpose                                |
|----------------|----------------------------------------|
| **Milvus**     | High-speed vector database             |
| **Streamlit**  | Web-based interactive user interface   |
| **FAISS**      | Approximate nearest neighbor indexing  |
| **scikit-learn** | PCA and preprocessing                |
| **Plotly**     | 3D visualization of embedding space    |
| **pandas/numpy** | Data processing                      |

---

## Links to Original JCP Data
## Dataset Overview

| Dataset  | Matches URL          | Feature Ranking URL       | Gallery URL             | Description           |
|----------|----------------------|----------------------------|--------------------------|------------------------|
| ORF      | [broad.io/orf](https://broad.io/orf)               | [broad.io/orf_feature](https://broad.io/orf_feature)     | [broad.io/orf_gallery](https://broad.io/orf_gallery)       | Gene overexpression  |
| CRISPR   | [broad.io/crispr](https://broad.io/crispr)         | [broad.io/crispr_feature](https://broad.io/crispr_feature) | [broad.io/crispr_gallery](https://broad.io/crispr_gallery) | Gene knock-out       |
| Compound | [broad.io/compound](https://broad.io/compound)     | [broad.io/feature](https://broad.io/feature)             | [broad.io/compound_gallery](https://broad.io/compound_gallery) | Chemical compounds    |



