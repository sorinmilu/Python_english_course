scores = [42, 88, 15]

labels = [
    "pass" if score >= 50 else "fail"
    for score in scores
]

print(f"scores: {scores}")
print(f"labels: {labels}")
