def add_def(x):
    return x + 42

add_lambda = lambda x: x + 42

for label, fn in [("add_def", add_def), ("add_lambda", add_lambda)]:
    print(f"{label}: type={type(fn)}, vars={fn.__code__.co_varnames}, "
          f"consts={fn.__code__.co_consts}, result={fn(8)}")
