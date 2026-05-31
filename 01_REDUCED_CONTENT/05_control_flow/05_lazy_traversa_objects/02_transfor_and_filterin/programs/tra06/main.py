def loud_text(text):
    print(f"transforming: {text}")
    return text.upper()

quotes = ["ni", "spam", "giddy up"]

loud_quotes = map(loud_text, quotes)

print("map object created")
print(f"type(loud_quotes): {type(loud_quotes)}")

print("asking for first value")
print(next(loud_quotes))

print("asking for second value")
print(next(loud_quotes))
