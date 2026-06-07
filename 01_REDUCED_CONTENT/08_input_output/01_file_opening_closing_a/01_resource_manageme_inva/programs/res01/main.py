path = "protocol_demo.txt"
file_obj = open(path, "w", encoding="utf-8")
entered = file_obj.__enter__()
entered.write("Protocol-driven write.\n")
file_obj.__exit__(None, None, None)
print(file_obj.closed)
