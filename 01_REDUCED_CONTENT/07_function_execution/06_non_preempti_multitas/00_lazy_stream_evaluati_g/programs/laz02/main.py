def count_quotes():
    yield "D'oh!"
    yield "No soup for you!"

gen = count_quotes()
print(f"type: {type(gen)}")
print(next(gen))
print(next(gen))
