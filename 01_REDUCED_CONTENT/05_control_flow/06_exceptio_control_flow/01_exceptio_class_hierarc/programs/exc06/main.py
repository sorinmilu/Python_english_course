items = ["soup", "pretzels"]

cases = [0, 42, "bad"]

for index in cases:
    try:
        item = items[index]
        print(f"index {index!r}: {item}")
    except (IndexError, TypeError) as err:
        print(f"index {index!r}: lookup failed")
        print(f"error type: {type(err)}")
        print(f"message: {err}")
