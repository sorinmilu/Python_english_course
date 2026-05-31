import sys

def sum_down(n):
    if n == 0:
        return 0
    return n + sum_down(n - 1)

print(f"sum_down(4)={sum_down(4)}")
print(f"recursion limit={sys.getrecursionlimit()}")
