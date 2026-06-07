path = "binary_mode_demo.bin"
data = b"Binary mode does not decode text. 42.\n"
with open(path, "wb") as f:
    f.write(data)
with open(path, "rb") as f:
    restored = f.read()
print(data == restored, type(restored))
