age_text = "forty-two"

if age_text:
    try:
        age = int(age_text)
        print(f"age: {age}")
    except ValueError:
        print("age text was not a valid integer")
else:
    print("no age was entered")
