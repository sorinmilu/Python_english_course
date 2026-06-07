import sys

fd = sys.stdout.fileno()
print(f"stdout fileno = {fd}")
name, score = "Kramer", 42
sys.stdout.write(f"{name:10} | score = {score:04d}\n")
sys.stdout.flush()
