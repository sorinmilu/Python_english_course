default_score = 42

def show_line(name, score=default_score):
    return f"{name}: {score}"

default_score = 999
print(show_line("Homer"))
print(f"stored default: {show_line.__defaults__}")
