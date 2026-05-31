def is_even(num):
    return num % 2 == 0

texts = ["10", "15", "20", "42", "99"]

even_nums = list(filter(is_even, map(int, texts)))

print(f"even_nums: {even_nums}")
print(f"first even number: {even_nums[0]}")
print(f"total: {sum(even_nums)}")
print(f"again total: {sum(even_nums)}")
