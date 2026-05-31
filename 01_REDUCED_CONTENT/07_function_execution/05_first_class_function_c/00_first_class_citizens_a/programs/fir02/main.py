DISPATCH = {
    "double": lambda x: x * 2,
    "square": lambda x: x * x,
}

def run(op, value):
    return DISPATCH[op](value)

print(run("double", 21))
print(run("square", 7))
