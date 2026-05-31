def is_even(num):
    return num % 2 == 0

nums = [10, 15, 20, 42, 99]

even_nums = list(filter(is_even, nums))

print(f"len(even_nums): {len(even_nums)}")
print(f"even_nums[0]: {even_nums[0]}")
print(f"even_nums[-1]: {even_nums[-1]}")
