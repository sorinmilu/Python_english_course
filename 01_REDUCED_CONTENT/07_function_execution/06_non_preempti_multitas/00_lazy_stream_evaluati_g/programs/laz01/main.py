def small_gen():
    x = "D'oh!"
    yield x

gen = small_gen()
print(f"gi_frame before next: {gen.gi_frame}")
print(f"f_locals: {gen.gi_frame.f_locals}")
value = next(gen)
print(f"yielded: {value!r}, gi_frame after: {gen.gi_frame}")
