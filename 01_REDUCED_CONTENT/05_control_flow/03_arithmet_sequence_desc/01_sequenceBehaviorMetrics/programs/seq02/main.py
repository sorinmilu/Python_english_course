nums = range(1, 4)

it1 = iter(nums)
it2 = iter(nums)

print(f"type(it1): {type(it1)}")
print(f"type(it2): {type(it2)}")
print(f"it1 is it2: {it1 is it2}")

print(f"next(it1): {next(it1)}")
print(f"next(it1): {next(it1)}")

print(f"next(it2): {next(it2)}")
