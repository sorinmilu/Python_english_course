def noisy_add(a, b):
    print(a + b)

def real_add(a, b):
    return a + b

x = noisy_add(20, 22)
y = real_add(20, 22)

print(f"x={x!r}, y={y!r}")
