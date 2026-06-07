names = ["Jerry", "Elaine", "Kramer", "Newman"]
scores = [72, 91]

try:
    for name, score in zip(names, scores, strict=True):
        print(f"{name:<8} | {score:>3}")
except ValueError as err:
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
