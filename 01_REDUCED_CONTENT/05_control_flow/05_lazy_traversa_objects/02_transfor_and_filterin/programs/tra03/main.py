texts = ["10", "20", "42"]

nums = map(int, texts)

print(f"type(texts): {type(texts)}")
print(f"type(nums): {type(nums)}")
print(f"dir(nums) sample: {dir(nums)[:12]}")

print(f"has __iter__: {'__iter__' in dir(nums)}")
print(f"has __next__: {'__next__' in dir(nums)}")
