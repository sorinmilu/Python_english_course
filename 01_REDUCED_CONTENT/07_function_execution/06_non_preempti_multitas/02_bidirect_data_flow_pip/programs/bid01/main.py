def echo():
    while True:
        received = yield
        print(f"got: {received!r}")

gen = echo()
next(gen)
gen.send("D'oh!")
gen.send("Ni!")
