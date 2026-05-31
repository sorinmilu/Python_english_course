def flexible(*args, **kwargs):
    return len(args), len(kwargs)

def fixed(a, b):
    return a + b

print(flexible(1, 2, 3, x=4))
print(fixed(1, 2))
