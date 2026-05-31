def make_multiplier(factor):
    def multiply(value):
        return value * factor

    return multiply


times_three = make_multiplier(3)

print(times_three(10))
