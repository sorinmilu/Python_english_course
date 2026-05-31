import inspect

def divide(a, b, /):
    return a / b

sig = inspect.signature(divide)
print(f"{sig}")
for name, param in sig.parameters.items():
    print(f"{name}: {param.kind}")
