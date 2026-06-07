bad_src = "if True:\n        print('spaces')\n\tprint('tab')\n"

try:
    compile(bad_src, "<mixed_tabs_spaces>", "exec")
except TabError as err:
    print(f"type(err): {type(err)}")
    print(f"is IndentationError: {isinstance(err, IndentationError)}")
    print(f"message: {err}")
    print(f"args: {err.args}")
