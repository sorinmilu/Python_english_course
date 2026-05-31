def min_length_validator(min_length):
    def validate(text):
        return len(text) >= min_length

    return validate


password_validator = min_length_validator(8)

print(password_validator("abc"))
print(password_validator("long-enough"))
