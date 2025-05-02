from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
import pandas as pd
from enrichment import enrich_with_babel

# --- Config ---
collection_name = "orf_embeddings"
input_path = "/Users/user/Desktop/INFO 602/JCP/Matches/ORF_Matches.parquet"
output_path = "/Users/user/Desktop/INFO 602/JCP/Matches/ORF_Matches_enriched.parquet"

# --- Connect to Milvus ---
connections.connect("default", host="localhost", port="19530")

# --- Reset collection if needed ---
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
    print(f"Dropped existing collection: {collection_name}")

# --- Enrich metadata and load enriched data ---
enrich_with_babel(input_path, output_path)
df = pd.read_parquet(output_path)

# --- Prepare schema ---
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

schema = CollectionSchema(fields, description="ORF embedding schema")
collection = Collection(name=collection_name, schema=schema)
print(f"Created collection: {collection_name}")

# --- Insert data in safe batches ---
batch_size = 10000
num_rows = len(df)

for start in range(0, num_rows, batch_size):
    end = min(start + batch_size, num_rows)
    batch = [
        df["Metadata_Source"].iloc[start:end].tolist(),
        df["Metadata_Plate"].iloc[start:end].tolist(),
        df["Metadata_Well"].iloc[start:end].tolist(),
        df["Metadata_JCP2022"].iloc[start:end].tolist(),
        df["pert_type"].iloc[start:end].tolist(),
        df["name"].iloc[start:end].tolist(),
        df[embedding_cols].iloc[start:end].values.tolist(),
    ]
    collection.insert(batch)
    print(f"Inserted rows {start} to {end}")

# --- Finalize collection ---
collection.flush()
collection.create_index("embedding", {
    "index_type": "FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
})

print(" ORF data enriched, inserted, and indexed successfully.")