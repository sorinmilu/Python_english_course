nums = range(0, 5)

try:
    nums[0] = 99
except TypeError as err:
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
