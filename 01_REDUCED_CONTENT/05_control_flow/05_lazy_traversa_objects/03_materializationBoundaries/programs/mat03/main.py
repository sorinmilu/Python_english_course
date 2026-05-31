def is_even(num):
    return num % 2 == 0

nums = [10, 15, 20, 42, 99]

even_iter = filter(is_even, nums)

try:
    print(even_iter[0])
except TypeError as err:
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
