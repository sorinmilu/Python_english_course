values = ["10", "twenty", "42"]

for text in values:
    try:
        number = int(text)
        print(f"{text!r:>8} -> {number:>3}")
    except ValueError as err:
        print(f"{text!r:>8} -> conversion failed")
        print(f"error type: {type(err)}")
        print(f"error args: {err.args}")
