import json
from pathlib import Path

path = Path("demo.json")
path.write_text('{"show": "Simpsons", "line": "D\'oh!"}', encoding="utf-8")
with open(path, encoding="utf-8") as f:
    data = json.load(f)
print(data)
