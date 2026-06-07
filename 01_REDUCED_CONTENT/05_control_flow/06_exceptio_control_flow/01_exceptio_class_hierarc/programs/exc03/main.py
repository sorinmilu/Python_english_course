items = ["10", "20", "42"]

try:
    for item in items:
        number = int(item)
        total = total + number
except Exception as err:
    print("some error happened")
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
