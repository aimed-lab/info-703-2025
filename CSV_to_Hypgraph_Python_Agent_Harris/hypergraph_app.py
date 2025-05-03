import streamlit as st
import pandas as pd
import inspect
import importlib

# import the library
import hypernestedx as hnx

# -- dynamically discover every public class & function in hypernestedx --
_members = inspect.getmembers(
    hnx,
    predicate=lambda obj: inspect.isclass(obj) or inspect.isfunction(obj)
)
ALL_MEMBERS = sorted(
    name for name, obj in _members
    if not name.startswith("_") and obj.__module__ == "hypernestedx"
)

st.set_page_config(page_title="HypernestedX Universal Explorer", layout="wide")
st.title("HypernestedX Streamlit Interface (All Features)")

# --- 1. Upload Dataset ---
st.header("1. Upload a dataset")
uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xls"])
df = None
if uploaded_file:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        st.success("✔ Dataset loaded successfully")
    except Exception as e:
        st.error(f"✖ Error loading dataset: {e}")

# --- 2. Preview & Describe ---
if df is not None:
    st.subheader("2. Data Preview & Info")
    st.dataframe(df.head())
    st.write(f"Rows: **{df.shape[0]}**, Columns: **{df.shape[1]}**")
    if st.checkbox("Show column datatypes"):
        st.write(df.dtypes)

    # --- 3. Configure HypernestedX Integration ---
    st.header("3. Configure HypernestedX Integration")
    node_id_cols = st.multiselect(
        "Select one or more columns to use as node identifiers",
        df.columns.tolist(),
        default=[df.columns[0]]
    )
    hyperedge_cols = st.multiselect(
        "Select one or more columns to define hyperedges (relationships)",
        df.columns.tolist()
    )
    feature_cols = st.multiselect(
        "Select columns for feature vector computation (optional)",
        df.columns.tolist()
    )
    description = st.text_area(
        "Provide a brief description of the dataset/columns", height=100
    )

    hyperedge_type = st.selectbox(
        "Select hyperedge type",
        ["SimpleHyperedge", "DirectedHyperedge", "NodeDirectedHyperedge", "NestingHyperedges"]
    )
    if hyperedge_type in ["DirectedHyperedge", "NodeDirectedHyperedge"] and len(hyperedge_cols) < 2:
        st.warning("⚠️ Please select at least two columns for directed hyperedges")

    # --- 4. Select hypernestedx Classes & Functions ---
    st.header("4. Select hypernestedx Classes & Functions")
    chosen = st.multiselect(
        "Choose which hypernestedx members to include in generated code",
        ALL_MEMBERS,
        default=["Hypergraph", "BaseNode", "SimpleHyperedge"]
    )

    # --- 5. Generate Code Snippet ---
    if st.button("Generate HypernestedX Code", key="gen_code"):
        code_lines = []

        # 5.1 Imports
        code_lines.append("import pandas as pd")
        if chosen:
            code_lines.append(f"from hypernestedx import {', '.join(chosen)}")
        code_lines.append("")

        # 5.2 Description
        if description:
            desc = description.replace("\n", " ")
            code_lines.append(f"# Description: {desc}")
            code_lines.append("")

        # 5.3 Load data
        code_lines.append("# --- Load the dataset")
        code_lines.append(f"df = pd.read_csv(r\"{uploaded_file.name}\")  # adjust path")
        code_lines.append("")

        # 5.4 Initialize Hypergraph
        code_lines.append("# --- Initialize Hypergraph")
        code_lines.append("hg = Hypergraph(graph_id='user_hg')")
        code_lines.append("")

        # 5.5 Add nodes
        code_lines.append("# --- Add nodes from selected ID columns")
        code_lines.append(f"id_cols = {node_id_cols + hyperedge_cols}")
        code_lines.append("all_ids = pd.unique(df[id_cols].values.ravel()).astype(str)")
        code_lines.append("for uid in all_ids:")
        code_lines.append("    hg.add_node(BaseNode(node_id=uid, node_type='entity', attributes={}))")
        code_lines.append("")

        # 5.6 Add edges
        if hyperedge_type == "SimpleHyperedge":
            for col in hyperedge_cols:
                code_lines.append(f"# --- SimpleHyperedge from column: {col}")
                code_lines.append(
                    f"he_{col} = SimpleHyperedge("
                    f"edge_id='he_{col}', "
                    f"nodes=df['{col}'].astype(str).tolist(), "
                    f"modality='{col}')"
                )
                code_lines.append(f"hg.add_edge(he_{col})")
                code_lines.append("")
        elif hyperedge_type == "DirectedHyperedge":
            src, tgt = hyperedge_cols[:2]
            code_lines.append("# --- DirectedHyperedge")
            code_lines.append("he = DirectedHyperedge(")
            code_lines.append(f"    edge_id='he_dir',")
            code_lines.append(f"    source_nodes=df['{src}'].astype(str).tolist(),")
            code_lines.append(f"    target_nodes=df['{tgt}'].astype(str).tolist(),")
            code_lines.append(f"    modality='{src}_{tgt}'")
            code_lines.append(")")
            code_lines.append("hg.add_edge(he)")
            code_lines.append("")
        elif hyperedge_type == "NodeDirectedHyperedge":
            src, tgt = hyperedge_cols[:2]
            code_lines.append("# --- NodeDirectedHyperedge")
            code_lines.append("he = NodeDirectedHyperedge(")
            code_lines.append(f"    edge_id='he_node_dir',")
            code_lines.append(f"    source_nodes=df['{src}'].astype(str).tolist(),")
            code_lines.append(f"    target_nodes=df['{tgt}'].astype(str).tolist(),")
            code_lines.append(f"    modality='{src}_{tgt}'")
            code_lines.append(")")
            code_lines.append("hg.add_edge(he)")
            code_lines.append("")
        else:  # NestingHyperedges
            code_lines.append("# --- Build child SimpleHyperedges")
            for col in hyperedge_cols:
                code_lines.append(
                    f"he_{col} = SimpleHyperedge("
                    f"edge_id='he_{col}', "
                    f"nodes=df['{col}'].astype(str).tolist(), "
                    f"modality='{col}')"
                )
            child_list = ", ".join(f"he_{c}" for c in hyperedge_cols)
            code_lines.append("")
            code_lines.append("# --- NestingHyperedges aggregator")
            code_lines.append(
                f"nest = NestingHyperedges("
                f"edge_id='nest1', "
                f"hyperedges=[{child_list}], "
                f"modality='nested')"
            )
            code_lines.append("hg.add_edge(nest)")
            code_lines.append("")

        # 5.7 Compute features
        if feature_cols:
            code_lines.append("# --- Compute feature vectors")
            code_lines.append(f"feature_keys = {feature_cols}")
            code_lines.append("for node in hg.nodes.values():")
            code_lines.append("    node.compute_features(feature_keys)")
            code_lines.append("")

        # 5.8 Compute matrices
        code_lines.append("# --- Compute incidence & adjacency matrices")
        code_lines.append("incidence = hg.compute_incidence_matrix()")
        code_lines.append("adjacency = hg.compute_adjacency_matrix()")
        code_lines.append("")

        # 5.9 TODO placeholders for other chosen members
        CORE = {
            "Hypergraph", "BaseNode", "SimpleHyperedge",
            "DirectedHyperedge", "NodeDirectedHyperedge", "NestingHyperedges",
            "compute_incidence_matrix", "compute_adjacency_matrix"
        }
        for name in chosen:
            if name not in CORE:
                code_lines.append(f"# TODO: demonstrate usage of {name}(...)")
                code_lines.append("")

        snippet = "\n".join(code_lines)

        # display & download
        st.subheader("Generated Code Snippet")
        st.code(snippet, language="python")
        st.download_button(
            "📥 Download Code Snippet",
            snippet,
            file_name="hypernestedx_snippet.py",
            mime="text/x-python"
        )

    # --- 6. Preview Hypergraph Construction ---
    st.header("5. Preview Hypergraph Construction")
    if st.button("Build & Preview Hypergraph", key="build_preview"):
        with st.spinner("Building hypergraph..."):
            try:
                hg2 = hnx.Hypergraph(graph_id="st_hg")
                all_ids = pd.unique(df[(node_id_cols + hyperedge_cols)].values.ravel()).astype(str)
                for uid in all_ids:
                    hg2.add_node(hnx.BaseNode(node_id=uid, node_type="entity", attributes={}))

                if hyperedge_type == "SimpleHyperedge":
                    for col in hyperedge_cols:
                        he = hnx.SimpleHyperedge(
                            edge_id=f"he_{col}",
                            nodes=df[col].astype(str).tolist(),
                            modality=col
                        )
                        hg2.add_edge(he)
                elif hyperedge_type == "DirectedHyperedge":
                    he = hnx.DirectedHyperedge(
                        edge_id="he_dir",
                        source_nodes=df[hyperedge_cols[0]].astype(str).tolist(),
                        target_nodes=df[hyperedge_cols[1]].astype(str).tolist(),
                        modality="directed"
                    )
                    hg2.add_edge(he)
                elif hyperedge_type == "NodeDirectedHyperedge":
                    he = hnx.NodeDirectedHyperedge(
                        edge_id="he_node_dir",
                        source_nodes=df[hyperedge_cols[0]].astype(str).tolist(),
                        target_nodes=df[hyperedge_cols[1]].astype(str).tolist(),
                        modality="node_directed"
                    )
                    hg2.add_edge(he)
                else:
                    child_hes = [
                        hnx.SimpleHyperedge(
                            edge_id=f"he_{col}",
                            nodes=df[col].astype(str).tolist(),
                            modality=col
                        )
                        for col in hyperedge_cols
                    ]
                    nest = hnx.NestingHyperedges(
                        edge_id="nest1",
                        hyperedges=child_hes,
                        modality="nested"
                    )
                    hg2.add_edge(nest)

                inc = hg2.compute_incidence_matrix()
                adj = hg2.compute_adjacency_matrix()

                st.success("✅ Hypergraph built successfully")
                st.write(f"• Nodes: **{len(hg2.nodes)}**, Edges: **{len(hg2.edges)}**")
                st.write(f"• Incidence matrix shape: {inc.shape}")
                st.write(f"• Adjacency matrix shape: {adj.shape}")

                if inc.size <= 2500:
                    st.dataframe(pd.DataFrame(inc, index=list(hg2.nodes), columns=list(hg2.edges)))
                if adj.shape[0] <= 50:
                    st.dataframe(pd.DataFrame(adj, index=list(hg2.nodes), columns=list(hg2.nodes)))

            except Exception as e:
                st.error(f"Error building hypergraph: {e}")

    # --- 7. Debugging Assistant ---
    st.header("6. Debugging Assistant")
    tb = st.text_area("Paste your Python traceback or error here", height=200, key="traceback")
    if st.button("Get Debug Suggestions", key="debug_suggest"):
        if "KeyError" in tb:
            st.error("⚠️ KeyError detected: Make sure all node IDs referenced in hyperedges have been created first.")
            st.info("Tip: collect unique IDs from all relevant columns before adding BaseNode entries.")
        elif "AttributeError" in tb:
            st.error("⚠️ AttributeError detected: Verify you imported the correct class or method name.")
            st.info("Tip: check your `from hypernestedx import ...` line for typos.")
        elif "ModuleNotFoundError" in tb or "ImportError" in tb:
            st.error("⚠️ Import error: Ensure the `hypernestedx` package is installed and up to date.")
        else:
            st.info("No common patterns found. Please review the full traceback or consult the docs.")