nums = range(0, 5)

try:
    nums.start = 100
except AttributeError as err:
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
