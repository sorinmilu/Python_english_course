items = ["soup", "pretzels"]

index = 2

try:
    print(f"item: {items[index]}")
except IndexError as err:
    print("index is outside the list")
    print(f"type(err): {type(err)}")
