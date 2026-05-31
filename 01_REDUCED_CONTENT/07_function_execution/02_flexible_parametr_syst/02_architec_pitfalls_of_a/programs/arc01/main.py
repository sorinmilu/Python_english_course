def add_quote(text, lines=None):
    if lines is None:
        lines = []
    lines.append(text)
    return lines

a = add_quote("D'oh!")
b = add_quote("Ni!")

print(f"a={a}, b={b}, a is b: {a is b}")
