text = "forty-two"

try:
    number = int(text)
except ValueError as err:
    print(f"type(err): {type(err)}")
    print(f"dir(err) sample: {dir(err)[:10]}")
    print(f"err.args: {err.args}")
    print(f"has __traceback__: {'__traceback__' in dir(err)}")
