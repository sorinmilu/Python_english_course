text = "Stiinta"
try:
    text.encode("ascii")
except UnicodeEncodeError as err:
    print(err)

data = text.encode("utf-8")
print(data.decode("utf-8"))
