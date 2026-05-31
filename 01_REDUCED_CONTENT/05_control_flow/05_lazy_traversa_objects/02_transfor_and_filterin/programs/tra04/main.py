def is_even(num):
    return num % 2 == 0

nums = [10, 15, 20, 42, 99]

for num in nums:
    if is_even(num):
        print(f"accepted: {num}")
