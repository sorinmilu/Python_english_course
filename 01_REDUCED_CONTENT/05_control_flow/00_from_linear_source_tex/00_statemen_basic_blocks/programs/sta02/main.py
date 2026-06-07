text = "forty-two"

print("before conversion")

try:
    number = int(text)
    print(f"number: {number}")
except ValueError as err:
    print("conversion failed")
    print(f"error type: {type(err)}")
    print(f"error message: {err}")

print("after try statement")
