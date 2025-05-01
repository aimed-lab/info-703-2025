"""
Graph Explorer: A Gradio-based UI for querying a Neo4j graph via natural language.
Prompts for pre-filtered CSV paths, Neo4j credentials, and Groq API details at runtime,
sets up LangChain Neo4jGraph and ChatGroq LLM, and launches the web interface.
"""
import os
import io
import re
import pandas as pd
import gradio as gr
from langchain_community.graphs import Neo4jGraph
from langchain_groq import ChatGroq
from langchain.chains import GraphCypherQAChain
from neo4j import exceptions as neo4j_exceptions
import contextlib

# Prompt for filtered CSV file paths
r2g_path = input("Enter path to R2G_validated.csv: ")
r2d_path = input("Enter path to R2D_filtered.csv: ")
d2g_path = input("Enter path to D2G_filtered.csv: ")
g2g_path = input("Enter path to G2G_filtered.csv: ")

R2G_validated = pd.read_csv(r2g_path)
R2D_filtered  = pd.read_csv(r2d_path)
D2G_filtered  = pd.read_csv(d2g_path)
G2G_filtered  = pd.read_csv(g2g_path)

neo4j_uri      = input("Enter Neo4j URI (e.g., neo4j+s://...): ")
neo4j_username = input("Enter Neo4j username: ")
neo4j_password = input("Enter Neo4j password: ")

groq_api_key = input("Enter Groq API key: ")
model_name   = input("Enter Groq model name: ")

all_genes = [""] + sorted(
    set(G2G_filtered['GENE_NAMES_1'].dropna().str.upper()) |
    set(G2G_filtered['GENE_NAMES_2'].dropna().str.upper()) |
    set(R2G_validated['gene_name'].dropna().str.upper()) |
    set(D2G_filtered['GENE_SYMBOL'].dropna().str.upper())
)
all_semantic_types = [""] + sorted(
    D2G_filtered['DISEASE_SEMANTIC_TYPE'].dropna().str.upper().unique().tolist()
)
all_drugs = [""] + sorted(
    set(R2G_validated['drug_name'].dropna().str.upper()) |
    set(R2D_filtered['DRUGBANK_NAME_DISGENET'].dropna().str.upper())
)
all_side_effects = [""] + sorted(
    R2D_filtered['SIDE_EFFECT'].dropna().str.upper().unique().tolist()
)

# Initialize Graph + LLM ──
graph = Neo4jGraph(
    url=neo4j_uri,
    username=neo4j_username,
    password=neo4j_password,
)
llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name=model_name,
)
graph.refresh_schema()
chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,
    allow_dangerous_requests=True,
    return_cypher=True,
    system_prompt="""
You are a Neo4j Cypher query generator. You know the schema:
- (g:Gene {name})
- (d:Disease {name})
- (d:Drug {name})
- (se:Side_effect {name})
Relationships:
- (Gene)-[:ASSOCIATED_WITH]->(GeneOrDisease)
- (Drug)-[:TREATS]->(Disease)
- (Drug)-[:HAS_SIDE_EFFECT]->(Side_effect)
Always output a full valid Cypher starting with MATCH. Do not emit standalone WHERE or partial queries.
"""
)

def get_disease_names(sem_type):
    df = D2G_filtered
    if sem_type:
        df = df[df['DISEASE_SEMANTIC_TYPE'].str.upper() == sem_type]
    opts = [""] + sorted(df['DISEASE_NAME'].dropna().str.upper().unique().tolist())
    return gr.update(choices=opts, value="")

def ask_graph(nl_query):
    if not nl_query.strip():
        return "", ""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            resp = chain.invoke({"query": nl_query})
        raw_logs = buf.getvalue()
        clean_logs = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", raw_logs)
        result = resp.get('result', resp.get('results', []))
        if isinstance(result, list):
            items = [next(iter(item.values()), '') if isinstance(item, dict) else str(item) for item in result]
            result_text = ", ".join(items)
        else:
            result_text = str(result)
        return clean_logs, result_text
    except neo4j_exceptions.CypherSyntaxError as e:
        raw_logs = buf.getvalue()
        clean_logs = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", raw_logs)
        return clean_logs, f"Cypher syntax error: {e}"
    except Exception as e:
        raw_logs = buf.getvalue()
        clean_logs = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", raw_logs)
        return clean_logs, f"Error: {e}"

with gr.Blocks(title="Graph Explorer") as demo:
    with gr.Row():
        gr.Column(scale=1)
        with gr.Column(scale=2, min_width=600):
            gr.Markdown("## Graph Explorer")
            gene_dd    = gr.Dropdown(all_genes,        label="Gene",              value="", interactive=True)
            sem_dd     = gr.Dropdown(all_semantic_types,label="Disease Semantic Type", value="", interactive=True)
            disease_dd = gr.Dropdown([""],            label="Disease Name",      value="", interactive=True)
            drug_dd    = gr.Dropdown(all_drugs,        label="Drug",              value="", interactive=True)
            side_dd    = gr.Dropdown(all_side_effects, label="Side Effect",       value="", interactive=True)
            sem_dd.change(get_disease_names, [sem_dd], [disease_dd])

            nl_txt   = gr.Textbox(label="Natural-Language Query", lines=2, max_lines=2)
            logs_txt = gr.Textbox(label="Logs",                  lines=12, max_lines=12)
            res_txt  = gr.Textbox(label="Result",                lines=4, max_lines=4)

            ask_btn = gr.Button("Ask Graph")
            ask_btn.click(fn=ask_graph, inputs=[nl_txt], outputs=[logs_txt, res_txt])
        gr.Column(scale=1)

if __name__ == "__main__":
    demo.launch()