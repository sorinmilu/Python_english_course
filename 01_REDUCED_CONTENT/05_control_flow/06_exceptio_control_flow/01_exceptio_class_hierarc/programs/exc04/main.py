texts = ["10", "20", "bad", "42"]

for text in texts:
    try:
        number = int(text)
        print(f"{text!r} -> {number}")
    except ValueError as err:
        print(f"{text!r} -> invalid integer text")
        print(f"message: {err}")
