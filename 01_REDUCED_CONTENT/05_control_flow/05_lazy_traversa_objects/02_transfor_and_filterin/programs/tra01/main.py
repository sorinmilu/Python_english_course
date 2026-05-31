def show_int(text):
    print(f"mapping: {text}")
    return int(text)

def is_large(num):
    print(f"filtering: {num}")
    return num > 20

texts = ["10", "20", "42", "100"]

nums = map(show_int, texts)
large_nums = filter(is_large, nums)

print("pipeline created")
print("asking for first accepted value")
print(next(large_nums))
