def bad_swap(a, b):
    a, b = b, a

x, y = "Arthur", "Patsy"
bad_swap(x, y)
print(f"after bad_swap: x={x!r}, y={y!r}")

x, y = y, x  # caller must rebind explicitly
print(f"after caller rebind: x={x!r}, y={y!r}")
