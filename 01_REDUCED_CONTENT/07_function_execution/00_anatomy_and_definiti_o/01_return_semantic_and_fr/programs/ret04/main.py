import inspect

def show_frame(n):
    frame = inspect.currentframe()
    print(f"n={n}, co_name={frame.f_code.co_name}, "
          f"locals={list(frame.f_locals.keys())}, f_back={frame.f_back is not None}")

show_frame(42)
