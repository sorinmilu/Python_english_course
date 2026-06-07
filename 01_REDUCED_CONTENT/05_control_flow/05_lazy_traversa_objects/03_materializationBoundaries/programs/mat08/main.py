names = ["Jerry", "Elaine", "Kramer"]

pairs = enumerate(names)

stored_list = list(pairs)

print(f"stored_list: {stored_list}")
print(f"type(stored_list): {type(stored_list)}")
print(f"dir(stored_list) sample: {dir(stored_list)[:10]}")
