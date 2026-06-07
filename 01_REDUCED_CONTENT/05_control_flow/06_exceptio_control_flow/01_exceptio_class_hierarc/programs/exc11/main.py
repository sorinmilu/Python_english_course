text = "forty-two"

try:
    number = int(text)
    print(f"number: {number}")
except Exception:
    print("general handler: catches the ValueError first")
except ValueError:
    print("specific handler: unreachable here")
