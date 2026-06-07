text = "forty-two"

print("before conversion")

try:
    number = int(text)
    print(f"number: {number}")
except ValueError as err:
    print("conversion failed")
    print(f"type(err): {type(err)}")
    print(f"message: {err}")

print("after conversion attempt")
