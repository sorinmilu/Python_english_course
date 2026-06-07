names = ["Jerry", "Elaine", "Kramer"]

pairs = enumerate(names, start=1)

print(f"pairs: {pairs}")
print("nothing has been printed from the names yet")

print(f"next(pairs): {next(pairs)}")
print(f"next(pairs): {next(pairs)}")
