def outer():
    message = "D'oh!"

    def inner():
        return message

    return inner

fn = outer()
print(f"fn(): {fn()}")
print(f"co_cellvars: {outer.__code__.co_cellvars}")
print(f"co_freevars: {fn.__code__.co_freevars}")
print(f"closure: {fn.__closure__}")
print(f"cell contents: {fn.__closure__[0].cell_contents!r}")
