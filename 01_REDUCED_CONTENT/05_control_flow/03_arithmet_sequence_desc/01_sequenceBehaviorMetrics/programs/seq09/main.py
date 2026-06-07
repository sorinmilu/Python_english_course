nums = range(10, 20, 2)

try:
    print(nums[99])
except IndexError as err:
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
