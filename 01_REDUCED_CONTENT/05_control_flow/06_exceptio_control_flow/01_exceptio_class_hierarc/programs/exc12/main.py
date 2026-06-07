text = "forty-two"

try:
    number = int(text)
    print(f"number: {number}")
except ValueError:
    print("specific handler: invalid integer text")
except Exception:
    print("general handler: some other ordinary exception")
