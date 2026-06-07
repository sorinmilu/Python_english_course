import io
import tokenize

src = """\
score = 42

if score == 42:
    print("the answer")
    print("do not panic")

print("done")
"""

tokens = tokenize.generate_tokens(io.StringIO(src).readline)

for tok in tokens:
    tok_name = tokenize.tok_name[tok.type]
    if tok_name in ("INDENT", "DEDENT", "NAME", "OP", "STRING", "NUMBER"):
        print(f"{tok_name:<8} {tok.string!r}")
