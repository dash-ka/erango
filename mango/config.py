from pathlib import Path
import tomllib

path = Path(__file__).parent / "recipe.toml"

with open(path, mode="rb") as fb:
    rules = tomllib.load(fb)

server = rules["server"]
column2type = rules["mapping"]
properties = rules["properties"]
relations = rules["relations"]
delimited_fields = rules["delimited_fields"]
