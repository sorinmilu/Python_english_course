value = 0

if value:
    print("truthy")
else:
    print("false by truth-value testing")

if value is None:
    print("missing value")
else:
    print("actual object present")
