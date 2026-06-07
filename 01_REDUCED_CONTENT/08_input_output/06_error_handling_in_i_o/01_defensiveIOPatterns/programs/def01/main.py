from pathlib import Path
path = Path("maybe.txt")
try:
    text = path.read_text(encoding="utf-8")
except FileNotFoundError:
    text = ""
print(text)
