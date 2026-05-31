def is_even(num):
    return num % 2 == 0

nums = [10, 15, 20, 42, 99]

even_nums = filter(is_even, nums)

print(f"type(nums): {type(nums)}")
print(f"type(even_nums): {type(even_nums)}")
print(f"dir(even_nums) sample: {dir(even_nums)[:12]}")

print(f"has __iter__: {'__iter__' in dir(even_nums)}")
print(f"has __next__: {'__next__' in dir(even_nums)}")
