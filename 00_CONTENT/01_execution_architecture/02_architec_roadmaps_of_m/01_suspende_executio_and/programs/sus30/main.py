def accumulator():
    total = 0

    while True:
        value = yield total
        total += value


acc = accumulator()

print(next(acc))      # starts coroutine, yields 0
print(acc.send(5))    # sends 5, yields 5
print(acc.send(7))    # sends 7, yields 12
