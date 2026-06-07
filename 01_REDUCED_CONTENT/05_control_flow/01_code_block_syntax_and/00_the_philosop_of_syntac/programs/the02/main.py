bad_src = """\
if True:
print("Ni!")
"""

try:
    compile(bad_src, "<bad_indent>", "exec")
except IndentationError as err:
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
    print(f"args: {err.args}")
    print(f"has lineno: {'lineno' in dir(err)}")
    print(f"line number: {err.lineno}")
