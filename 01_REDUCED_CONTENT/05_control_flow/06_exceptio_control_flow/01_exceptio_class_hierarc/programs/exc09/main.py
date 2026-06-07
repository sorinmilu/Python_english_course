scores = {
    "Jerry": 72,
    "Elaine": 91,
}

name = "Kramer"

try:
    print(scores[name])
except LookupError:
    print("general lookup handler")
except KeyError:
    print("specific handler: unreachable here")
