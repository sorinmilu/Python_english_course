def make_counter():
    count = 0

    def next_value():
        nonlocal count
        count += 1
        return count

    return next_value


counter = make_counter()

print(counter())
print(counter())
print(counter())
