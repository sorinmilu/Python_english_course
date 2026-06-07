try:
    score = int("D'oh!")
except ValueError as err:
    print(f"type(err): {type(err)}")
    print(f"dir(err) sample: {dir(err)[:12]}")
    print(f"err.args: {err.args}")
    print(f"str(err): {str(err)}")
    print(f"repr(err): {repr(err)}")
