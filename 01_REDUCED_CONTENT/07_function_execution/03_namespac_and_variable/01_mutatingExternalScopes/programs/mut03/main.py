answer = 42

def set_answer():
    answer = 100
    print(f"inside: {answer}")

set_answer()
print(f"outside: {answer}")
