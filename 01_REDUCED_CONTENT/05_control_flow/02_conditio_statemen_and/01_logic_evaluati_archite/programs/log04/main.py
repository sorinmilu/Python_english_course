quote = "Ni!"

print(f"quote: {quote!r}")
print(f"type(quote): {type(quote)}")
print(f"bool(quote): {bool(quote)}")
print(f"len(quote): {len(quote)}")
print(f"quote.__len__(): {quote.__len__()}")
print(f"has __len__: {'__len__' in dir(quote)}")
