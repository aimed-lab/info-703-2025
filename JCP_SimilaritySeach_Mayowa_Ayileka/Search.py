from pymilvus import connections, Collection
import pandas as pd
from Export import export_results_with_metadata




def run_vector_search(collection, query_vector, k, output_fields=None):
    """
    Perform a vector similarity search in Milvus.

    Parameters:
    - collection: Milvus collection object
    - query_vector: list of floats, the vector to search with
    - k: number of nearest neighbors to return
    - output_fields: list of additional metadata fields to return

    Returns:
    - Search results object
    """
    results = collection.search(
        data=[query_vector],
        anns_field="embedding",
        param={"metric_type": "L2", "params": {"nprobe": 10}},
        limit=k,
        output_fields=output_fields or []
    )
    return results

# Connect
connections.connect("default", host="localhost", port="19530")

# Load collection
collection = Collection("orf_embeddings")
collection.load()
print("Total entities:", collection.num_entities)

# Loading query vector
import pandas as pd
df = pd.read_parquet("/Users/user/Desktop/INFO 602/JCP/Matches/ORF_Matches.parquet")
embedding_cols = [col for col in df.columns if col.startswith("X_")]

#Picks xth vector
query_vector = df[embedding_cols].iloc[193].tolist()
print("Query vector length:", len(query_vector))

metadata_cols = ["Metadata_Source", "Metadata_Plate", "Metadata_Well", "Metadata_JCP2022"]

# Run search with all metadata fields
results = run_vector_search(collection, query_vector, k=5, output_fields=metadata_cols)

# for hits in results:
#     for hit in hits:
#         print(f"Distance: {hit.distance}, Metadata: {hit.entity.get('Metadata_JCP2022')}")




# export_results_with_metadata(results, df, metadata_cols, "orf.results.json")  