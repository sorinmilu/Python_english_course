try:
    number = int("forty-two")
except ValueError as err:
    print(f"err: {err}")
    print(f"type(err): {type(err)}")
    print(f"is ValueError: {isinstance(err, ValueError)}")
    print(f"is Exception: {isinstance(err, Exception)}")
    print(f"is BaseException: {isinstance(err, BaseException)}")
