num1 = 42
num2 = 0

print(f"type(num1): {type(num1)}")
print(f"bool(num1): {bool(num1)}")
print(f"num1.__bool__(): {num1.__bool__()}")
print(f"has __bool__: {'__bool__' in dir(num1)}")
print(f"has __len__: {'__len__' in dir(num1)}")

print(f"bool(num2): {bool(num2)}")
print(f"num2.__bool__(): {num2.__bool__()}")
