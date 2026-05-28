def count_up_to(limit):
    current = 1

    while current <= limit:
        yield current
        current += 1


g = count_up_to(3)

print(next(g))  # 1
print(next(g))  # 2
print(next(g))  # 3
