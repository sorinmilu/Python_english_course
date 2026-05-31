def say_doh():
    return "D'oh!"

fn = say_doh
print(f"fn is say_doh: {fn is say_doh}, fn(): {fn()}")

def apply_twice(fn, arg):
    return fn(fn(arg))

def add_one(x):
    return x + 1

print(apply_twice(add_one, 10))
