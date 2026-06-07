scores = {
    "Jerry": 72,
    "Elaine": 91,
}

name = "Kramer"

try:
    print(scores[name])
except KeyError:
    print("specific handler: missing dictionary key")
except LookupError:
    print("general lookup handler")
