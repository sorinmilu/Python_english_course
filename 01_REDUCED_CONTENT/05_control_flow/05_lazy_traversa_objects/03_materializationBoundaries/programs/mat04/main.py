names = ["Jerry", "Elaine", "Kramer"]
scores = [72, 91, 42]

pairs = zip(names, scores)

stored = tuple(pairs)

print(f"stored: {stored}")
print(f"type(stored): {type(stored)}")
print(f"dir(stored) sample: {dir(stored)[:10]}")
