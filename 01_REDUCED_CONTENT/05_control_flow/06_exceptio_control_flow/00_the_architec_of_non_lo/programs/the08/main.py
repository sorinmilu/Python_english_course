scores = {
    "Jerry": 72,
    "Elaine": 91,
    "Kramer": 42,
}

print(f"type(scores): {type(scores)}")
print(f"dir(scores) sample: {dir(scores)[:12]}")
print(f"has __getitem__: {'__getitem__' in dir(scores)}")
print(f"has get: {'get' in dir(scores)}")
print(f"has keys: {'keys' in dir(scores)}")
