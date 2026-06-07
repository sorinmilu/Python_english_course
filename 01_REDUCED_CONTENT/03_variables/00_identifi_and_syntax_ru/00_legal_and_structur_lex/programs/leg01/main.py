import keyword

for name in ("def", "class", "print", "type", "answer_42"):
    print(f"{name:<12} keyword={keyword.iskeyword(name)}")
# def          keyword=True
# class        keyword=True
# print        keyword=False   <- maskable at runtime
# type         keyword=False   <- maskable at runtime
# answer_42    keyword=False
