names = ["Jerry", "Elaine", "Kramer"]
pairs = enumerate(names)

pair1 = next(pairs)
pair2 = next(pairs)
pair3 = next(pairs)

print(f"pair1: {pair1}")
print(f"pair2: {pair2}")
print(f"pair3: {pair3}")

print(f"type(pair1): {type(pair1)}")
print(f"dir(pair1) sample: {dir(pair1)[:10]}")
