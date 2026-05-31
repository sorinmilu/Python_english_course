def is_even(num):
    return num % 2 == 0

nums = [10, 20, 42]

even_nums = filter(is_even, nums)

first = list(even_nums)
second = list(even_nums)

print(f"first: {first}")
print(f"second: {second}")
