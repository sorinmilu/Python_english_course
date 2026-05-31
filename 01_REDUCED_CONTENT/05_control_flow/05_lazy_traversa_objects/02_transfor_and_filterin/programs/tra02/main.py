def is_even(num):
    return num % 2 == 0

texts = ["10", "15", "20", "42"]

nums = map(int, texts)
even_nums = filter(is_even, nums)

print(list(even_nums))
