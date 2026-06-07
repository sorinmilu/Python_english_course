path = "manual_close_demo.txt"
file_obj = open(path, "w", encoding="utf-8")
file_obj.write("No soup for you!\n")
print(file_obj.closed)
file_obj.close()
print(file_obj.closed)
