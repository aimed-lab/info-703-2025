import json

def export_results_with_metadata(results, original_df, metadata_fields, filename="results.json"):
    """
    Export search results with metadata into a JSON file.

    Args:
        results: Milvus search result object
        original_df: DataFrame with all metadata
        metadata_fields: List of metadata column names to export
        filename: JSON file to save results to
    """
    output = []

    for hit in results[0]:  # single query vector
        row_id = hit.id

        entry = {
            "id": str(row_id),
            "distance": float(hit.distance)
        }

        # Safely fetch each metadata field
        if hit.entity is not None:
            for key in metadata_fields:
                value = getattr(hit.entity, key, None)
                entry[key] = value

               

        output.append(entry)

    with open(filename, "w") as f:
        json.dump(output, f, indent=2)

    print(f" Exported {len(output)} results with metadata to {filename}")