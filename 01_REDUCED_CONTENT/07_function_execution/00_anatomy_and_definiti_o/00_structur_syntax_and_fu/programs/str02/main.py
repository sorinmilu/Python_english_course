def make_message(name, number=42):
    text = f"{name} says {number}"
    return text.upper()

code_obj = make_message.__code__

print(f"co_argcount:    {code_obj.co_argcount}")
print(f"co_varnames:    {code_obj.co_varnames}")
print(f"co_consts:      {code_obj.co_consts}")
print(f"co_names:       {code_obj.co_names}")
print(f"co_code length: {len(code_obj.co_code)}")
