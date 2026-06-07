age_text = "forty-two"

try:
    age = int(age_text)
    print(f"age: {age}")
except ValueError:
    print("age text was not a valid integer")
