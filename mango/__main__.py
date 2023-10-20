import json
import pandas as pd
from collections import defaultdict
from pathlib import Path
from alive_progress import alive_bar

import mango.mangopie as mp
from mango.cli import args
from mango.util import process_field
from mango.config import server, relations, column2type, properties, delimited_fields


def main():

    # read excel with annotated columns
    data = pd.read_excel(args.path)

    # instantiate Mango class to manage interaction with ERA APIs
    mg = mp.Mango(server["url"])

    print("Authenticating to server...")
    mg.authenticate(server["user"], server["password"])


    # POST annotated columns as entities
    print("Posting entities to db...")
    logged_entities = defaultdict(dict)

    for column_name, entity_type in column2type.items():
    
        if (delimiter := delimited_fields.get(column_name)):
            values = process_field(data[column_name].dropna().unique(), delimiter=delimiter)
        else:
            values = data[column_name].dropna().unique()

        ids = {}
        if (props:= properties.get(column_name)):

            # if an entity has properties write with properties
            for _, row in data[[column_name] + list(props)].drop_duplicates().iterrows():
                item = row.pop(column_name)
                params = {
                    f_name:value for p_name, f_name in properties[column_name].items() if (value:=row.get(p_name))
                    }
                ids[item] = mg.merge_entity(entity_type, item, params=params) 
        else:
            # if an entity lacks properties write a simple entity
            ids = {item : mg.merge_entity(entity_type, item) for item in values}

        logged_entities[column_name] = ids
        print(f"Merged {len(ids)} entities of type {entity_type} from column {column_name}")


    folder = Path.cwd()/"output"
    if not folder.exists():
        folder.mkdir()
    filename = folder/"entitied.json"
    filename.touch(exist_ok=True)  
    with open(filename, "w") as outfile: 
        json.dump(logged_entities, outfile, indent=4)


    # POST named relations between entity types
    print("\Posting relations to db...")
    logs = defaultdict(lambda:defaultdict(list))
    with alive_bar(len(data)) as bar:
        for _, row in data.iterrows():
            for r in relations:
                relation_name, col1, col2 = r["name"], r["entity1"], r["entity2"]

                if not (isinstance(row[col1], float) | isinstance(row[col2], float)):

                    if (delimiter := delimited_fields.get(col1)):
                        entities1 = process_field(row[col1], delimiter=delimiter) 
                    else:
                        entities1 = [row[col1]]
                        
                    if (delimiter := delimited_fields.get(col2)):
                        entities2 = process_field(row[col2], delimiter=delimiter)
                    else:
                        entities2 = [row[col2]]
                        
                    for e1 in entities1:
                        for e2 in entities2:

                            e1_display_type, e2_display_type = column2type[col1], column2type[col2]

                            entity1_id = mg.merge_entity(e1_display_type, e1)
                            entity2_id = mg.merge_entity(e2_display_type, e2)

                            logs[relation_name][col1].append(
                                mg.merge_relation(
                                    relation_name,
                                    mg.active_entities[e1_display_type],
                                    mg.active_entities[e2_display_type],
                                    entity1_id, entity2_id
                                    )
                                )  
            bar()

    
    filename = folder/"relations.json"
    filename.touch(exist_ok=True) 
    with open(filename, "w") as outfile: 
        json.dump(logs, outfile, indent=4)

if __name__ == "__main__":
    main()

