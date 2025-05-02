import pandas as pd
import polars as pl
from broad_babel.query import run_query

def enrich_with_babel(input_path: str, output_path: str):
    '''
    Enrich a raw .parquet file with 'pert_type' and 'name' using Babel metadata.

    Parameters:
    - input_path (str): Full path to the raw input .parquet file
    - output_path (str): Full path to save the enriched .parquet file
    '''

    # Load the raw data
    df = pd.read_parquet(input_path)

    # Convert to Polars for transformation
    pl_df = pl.from_pandas(df)
    flat_ids = pl_df.select("Metadata_JCP2022").unique().get_column("Metadata_JCP2022").explode().to_list()
    unique_ids = [x[0] if isinstance(x, list) else x for x in flat_ids]

    # Query Babel metadata
    query_result = run_query(
        query=tuple(unique_ids),
        input_column="JCP2022",
        output_column="JCP2022,pert_type,standard_key"
    )

    # Build dictionaries
    pert_mapper = {row[0]: row[1] for row in query_result}
    name_mapper = {row[0]: row[2] for row in query_result}

    # Add new columns
    pl_df = pl_df.with_columns([
        pl.col("Metadata_JCP2022").replace(pert_mapper).alias("pert_type"),
        pl.col("Metadata_JCP2022").replace(name_mapper).alias("name")
    ])

    # Save as enriched .parquet
    enriched_df = pl_df.to_pandas()
    enriched_df.to_parquet(output_path, index=False)
    print(f"Enriched file saved to: {output_path}")

