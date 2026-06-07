data = ["soup", "pretzels"]

try:
    print(data[42])
except LookupError as err:
    print("lookup failed")
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
