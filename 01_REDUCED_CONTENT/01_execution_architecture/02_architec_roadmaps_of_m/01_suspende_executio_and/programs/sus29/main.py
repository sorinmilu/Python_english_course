def task(name, count):
    for i in range(count):
        print(name, i)
        yield


tasks = [task("A", 3), task("B", 3)]

while tasks:
    current = tasks.pop(0)

    try:
        next(current)
        tasks.append(current)
    except StopIteration:
        pass
