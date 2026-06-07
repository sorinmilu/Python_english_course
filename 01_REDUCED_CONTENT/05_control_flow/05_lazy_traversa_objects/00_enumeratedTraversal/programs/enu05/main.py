names = ["Jerry", "Elaine", "Kramer"]

pairs = enumerate(names)

print(f"type(names): {type(names)}")
print(f"type(pairs): {type(pairs)}")
print(f"dir(pairs) sample: {dir(pairs)[:12]}")

print(f"has __iter__: {'__iter__' in dir(pairs)}")
print(f"has __next__: {'__next__' in dir(pairs)}")
