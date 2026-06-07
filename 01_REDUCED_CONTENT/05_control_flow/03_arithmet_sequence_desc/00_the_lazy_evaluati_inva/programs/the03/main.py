import sys

small_range = range(10)
large_range = range(1_000_000)
huge_range = range(1_000_000_000)

print(f"small_range: {small_range}")
print(f"large_range: {large_range}")
print(f"huge_range:  {huge_range}")

print(f"size of small_range: {sys.getsizeof(small_range)} bytes")
print(f"size of large_range: {sys.getsizeof(large_range)} bytes")
print(f"size of huge_range:  {sys.getsizeof(huge_range)} bytes")
