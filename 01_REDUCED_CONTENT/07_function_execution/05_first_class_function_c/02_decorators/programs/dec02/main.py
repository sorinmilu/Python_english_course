def make_logged(fn):
    def wrapper(*args, **kwargs):
        print(f"calling {fn.__name__}")
        return fn(*args, **kwargs)
    return wrapper

@make_logged
def shout(text):
    return text.upper()

print(shout("ni!"))
