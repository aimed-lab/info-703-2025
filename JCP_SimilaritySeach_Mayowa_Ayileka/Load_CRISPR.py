from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
import pandas as pd
from enrichment import enrich_with_babel

# --- Configuration ---
collection_name = "crispr_embeddings"
input_path = "/Users/user/Desktop/INFO 602/JCP/Matches/CRISPR_Matches.parquet"
output_path = "/Users/user/Desktop/INFO 602/JCP/Matches/CRISPR_Matches_enriched.parquet"

# --- Connect to Milvus ---
connections.connect("default", host="localhost", port="19530")

# --- Drop existing collection if needed ---
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
    print(f"Dropped existing collection: {collection_name}")

# --- Enrich metadata using Babel and load enriched data ---
enrich_with_babel(input_path, output_path)
df = pd.read_parquet(output_path)

# --- Prepare Milvus collection ---
embedding_cols = [col for col in df.columns if col.startswith("X_")]
dim = len(embedding_cols)

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="Metadata_Source", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="Metadata_Plate", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="Metadata_Well", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="Metadata_JCP2022", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="pert_type", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=128),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
]
schema = CollectionSchema(fields, description="CRISPR embedding schema")
collection = Collection(name=collection_name, schema=schema)
print(f"Created collection: {collection_name}")

# --- Insert + index ---
data_to_insert = [
    df["Metadata_Source"].tolist(),
    df["Metadata_Plate"].tolist(),
    df["Metadata_Well"].tolist(),
    df["Metadata_JCP2022"].tolist(),
    df["pert_type"].tolist(),
    df["name"].tolist(),
    df[embedding_cols].values.tolist()
]

collection.insert(data_to_insert)
collection.flush()
collection.create_index("embedding", {
    "index_type": "FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
})

print("CRISPR data enriched, inserted, and indexed successfully.")