text = "forty-two"

try:
    number = int(text)
except ValueError as err:
    print(f"type(err): {type(err)}")
    print(f"str(err): {str(err)}")
    print(f"args: {err.args}")
    print(f"has __traceback__: {'__traceback__' in dir(err)}")
