names = ["Jerry", "Elaine", "Kramer"]

stored = list(enumerate(names))

print("first traversal")
for pair in stored:
    print(pair)

print("second traversal")
for pair in stored:
    print(pair)
