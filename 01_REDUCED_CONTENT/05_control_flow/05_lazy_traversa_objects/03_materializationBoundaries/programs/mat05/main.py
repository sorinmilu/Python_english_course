def is_even(num):
    return num % 2 == 0

nums = [10, 15, 20, 42, 99]

even_iter = filter(is_even, nums)
even_nums = list(even_iter)

print(f"even_nums: {even_nums}")
print(f"type(even_nums): {type(even_nums)}")
