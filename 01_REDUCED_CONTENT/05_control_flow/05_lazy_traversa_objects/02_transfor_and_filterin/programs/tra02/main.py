text = "42"
num = int(text)

print(f"text: {text!r}")
print(f"type(text): {type(text)}")
print(f"num: {num}")
print(f"type(num): {type(num)}")
print(f"dir(num) sample: {dir(num)[:10]}")
print(f"num.__bool__(): {num.__bool__()}")
print(f"num.__add__(8): {num.__add__(8)}")
