value = 42

def broken():
    print(value)
    value = 100

try:
    broken()
except UnboundLocalError as err:
    print(err)
