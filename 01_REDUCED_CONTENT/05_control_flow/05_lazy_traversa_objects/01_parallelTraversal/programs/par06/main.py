names = ["Jerry", "Elaine", "Kramer"]
scores = [72, 91, 42]

for pair in zip(names, scores):
    name = pair[0]
    score = pair[1]
    print(f"{name:<8} | {score:>3}")
