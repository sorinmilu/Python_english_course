try:
    number = int(text)
except ValueError as err:
    print(f"conversion failed: {err}")
else:
    print(f"number: {number}")   # runs only on clean try completion
