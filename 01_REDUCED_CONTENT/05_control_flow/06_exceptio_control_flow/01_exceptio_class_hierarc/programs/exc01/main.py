try:
    number = int("D'oh!")
except Exception as err:
    print("unexpected failure during conversion block")
    print(f"type(err): {type(err)}")
    print(f"message: {err}")
    raise
