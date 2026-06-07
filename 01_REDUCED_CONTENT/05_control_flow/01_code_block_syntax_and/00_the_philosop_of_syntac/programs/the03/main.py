import io
import tokenize

src = "x = 42\n"
tokens = tokenize.generate_tokens(io.StringIO(src).readline)

first_tok = next(tokens)

print(f"type(first_tok): {type(first_tok)}")
print(f"first_tok: {first_tok}")
print(f"first_tok.type: {first_tok.type}")
print(f"first_tok.string: {first_tok.string!r}")
print(f"has start: {'start' in dir(first_tok)}")
print(f"has end: {'end' in dir(first_tok)}")
print(f"has line: {'line' in dir(first_tok)}")
