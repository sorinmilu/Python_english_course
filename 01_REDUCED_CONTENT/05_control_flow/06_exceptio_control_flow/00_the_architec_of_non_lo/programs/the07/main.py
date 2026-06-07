scores = {
    "Jerry": 72,
    "Elaine": 91,
    "Kramer": 42,
}

name = "Newman"
score = scores.get(name, "not found")

print(f"name: {name}")
print(f"score: {score}")
