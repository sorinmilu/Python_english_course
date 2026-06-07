scores = {
    "Jerry": 72,
    "Elaine": 91,
    "Kramer": 42,
}

name = "Newman"

if name in scores:
    score = scores[name]
    print(f"{name}: {score}")
else:
    print(f"{name} was not found")
