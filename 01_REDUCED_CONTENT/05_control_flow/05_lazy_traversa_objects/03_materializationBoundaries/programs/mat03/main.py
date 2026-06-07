names = ["Jerry", "Elaine"]

stored = tuple(enumerate(names))

try:
    stored.append((2, "Kramer"))
except AttributeError as err:
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
