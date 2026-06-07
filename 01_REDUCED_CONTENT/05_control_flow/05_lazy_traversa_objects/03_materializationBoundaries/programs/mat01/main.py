import sys

nums_range = range(1_000_000)
nums_map = map(lambda n: n * 2, nums_range)

print(f"type(nums_range): {type(nums_range)}")
print(f"type(nums_map): {type(nums_map)}")

print(f"size of range: {sys.getsizeof(nums_range)} bytes")
print(f"size of map:   {sys.getsizeof(nums_map)} bytes")
