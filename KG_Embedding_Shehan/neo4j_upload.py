# File: neo4j_upload.py
"""
Module to upload triplets DataFrame to a Neo4j graph database.
Contains a single function `upload_to_neo4j` which accepts a pandas DataFrame
of triplets and credentials for Neo4j.
"""
from neo4j import GraphDatabase


def upload_to_neo4j(triplets_df, uri, username, password):
    """
    Uploads triplets from a DataFrame to Neo4j.

    Parameters:
    - triplets_df: pandas.DataFrame with columns ['subject', 'predicate', 'object']
         -Example:
            subject	                       predicate	                                        object
            ABAT	                       gene/associated_with/DISEASE_OR_SYNDROME/disease	    TONIC - CLONIC SEIZURES
            TONIC - CLONIC SEIZURES	d      isease/has_class/disease_class	                    c23

    - uri: Neo4j URI (e.g., 'neo4j+s://<host>')
    - username: Neo4j username
    - password: Neo4j password
    """
    driver = GraphDatabase.driver(uri, auth=(username, password))

    def delete_all(tx):
        tx.run("MATCH (n) DETACH DELETE n")

    def upload_triplet(tx, subject, predicate, object_):
               
        parts = predicate.split('/')
        if len(parts) < 2:
            return  
        subject_label = parts[0].capitalize()
        relation_type = parts[1].upper().replace("-", "_")
        edge_property = None
        object_label = "Entity"

        if len(parts) == 4:
            edge_property = parts[2]
            object_label = parts[3].capitalize()
        elif len(parts) == 3:
            object_label = parts[2].capitalize()

        query = f"""
        MERGE (a:{subject_label} {{name: $subject}})
        MERGE (b:{object_label} {{name: $object}})
        MERGE (a)-[r:{relation_type}]->(b)
        """
        params = {"subject": subject, "object": object_}
        if edge_property:
            query += "\nSET r.property = $edge_property"
            params["edge_property"] = edge_property

        tx.run(query, **params)

 
    with driver.session() as session:
        session.execute_write(delete_all)
        print(" Existing graph cleared.")
        print(" Uploading triplets...")
        for _, row in triplets_df.iterrows():
            session.execute_write(upload_triplet,
                                   row['subject'],
                                   row['predicate'],
                                   row['object'])
    driver.close()
    print(" Graph upload complete!")


if __name__ == '__main__':
    import pandas as pd
    import getpass

    # Prompt user for inputs
    csv_path = input("Enter path to triplets CSV file: ")
    triplets = pd.read_csv(csv_path)

    uri = input("Enter Neo4j URI (e.g., neo4j+s://...): ")
    username = input("Enter Neo4j username: ")
    password = getpass.getpass("Enter Neo4j password: ")

    upload_to_neo4j(triplets, uri, username, password)