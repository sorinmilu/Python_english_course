names = ["Jerry", "Elaine", "Kramer", "Newman"]
scores = [72, 91]

print(f"len(names): {len(names)}")
print(f"len(scores): {len(scores)}")

if len(names) != len(scores):
    print("length mismatch")
else:
    for name, score in zip(names, scores):
        print(f"{name:<8} | {score:>3}")
