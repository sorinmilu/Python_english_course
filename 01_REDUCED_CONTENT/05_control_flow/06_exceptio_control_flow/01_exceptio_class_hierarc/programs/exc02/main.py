items = ["10", "20", "42"]
total = 0

for item in items:
    try:
        number = int(item)
    except ValueError as err:
        print(f"invalid integer text: {item!r}")
        print(f"message: {err}")
    else:
        total = total + number

print(f"total: {total}")
