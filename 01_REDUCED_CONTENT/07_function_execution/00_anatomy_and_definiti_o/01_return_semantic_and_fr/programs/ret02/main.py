def get_pair():
    return "Homer", 42

result = get_pair()
label, code = get_pair()

print(f"result={result}, type={type(result)}")
print(f"label={label!r}, code={code!r}")
