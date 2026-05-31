def change_number(n):
    n = n + 1

def add_line(lines):
    lines.append("extra")

x = 42
quotes = ["D'oh!"]

change_number(x)
add_line(quotes)

print(f"x={x}, quotes={quotes}")
