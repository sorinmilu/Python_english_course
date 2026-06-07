names = ["Jerry", "Elaine", "Kramer"]
scores = [72, 91, 42]

pairs = zip(names, scores)

stored = list(pairs)

print(f"stored: {stored}")
print(f"type(stored): {type(stored)}")
