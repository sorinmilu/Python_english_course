def apply_to_values(values, callback):
    results = []

    for value in values:
        results.append(callback(value))

    return results


def square(x):
    return x * x


print(apply_to_values([1, 2, 3], square))
