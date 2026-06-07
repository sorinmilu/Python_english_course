text = "42"

try:
    number = int(text)
    print(f"number: {number}")
except ValueError as err:
    print(f"conversion failed: {err}")

print("after try")
