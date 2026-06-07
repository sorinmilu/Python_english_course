import sys

nums_range = range(1_000_000)
nums_list = list(nums_range)

print(f"type(nums_range): {type(nums_range)}")
print(f"type(nums_list): {type(nums_list)}")

print(f"size of nums_range: {sys.getsizeof(nums_range)} bytes")
print(f"size of nums_list:  {sys.getsizeof(nums_list)} bytes")
