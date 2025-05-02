from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection

# ---- CONNECT TO MILVUS ----
connections.connect("default", host="localhost", port="19530")

# ---- Shared schema settings ----
collections = {
    "orf_embeddings": 259,
    "crispr_embeddings": 259
}

metadata_fields = [
    "Metadata_Source",
    "Metadata_Plate",
    "Metadata_Well",
    "Metadata_JCP2022",
    "pert_type",
    "name"
]

# ---- Reset each collection ----
for name, vector_dim in collections.items():
    if utility.has_collection(name):
        utility.drop_collection(name)
        print(f" Dropped collection: {name}")

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True)
    ]
    for field in metadata_fields:
        fields.append(FieldSchema(name=field, dtype=DataType.VARCHAR, max_length=256))
    fields.append(FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=vector_dim))

    schema = CollectionSchema(fields, description=f"{name} schema")
    Collection(name=name, schema=schema)
    print(f" Created collection: {name} with fields {[f.name for f in fields]}")