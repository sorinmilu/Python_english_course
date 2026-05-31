def add_quote(text, lines=[]):
    lines.append(text)
    return lines

a = add_quote("D'oh!")
b = add_quote("No soup for you!")

print(f"a={a}")
print(f"b={b}, a is b: {a is b}")
print(f"stored default: {add_quote.__defaults__}")
