steps = range(1, 6)

print("plain traversal")
for n in steps:
    print(f"n: {n}")

print("squared values")
for n in steps:
    print(f"{n} squared is {n * n}")

print("formatted table")
for n in steps:
    print(f"{n:>2} | {n * 42:>3}")
