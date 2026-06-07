texts = ["10", "20", "42"]

nums_iter = map(int, texts)
nums = list(nums_iter)

print(f"nums: {nums}")
print(f"type(nums): {type(nums)}")
print(f"nums[0]: {nums[0]}")
print(f"sum(nums): {sum(nums)}")
