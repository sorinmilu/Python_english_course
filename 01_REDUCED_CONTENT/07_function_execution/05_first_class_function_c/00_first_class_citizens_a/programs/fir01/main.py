def make_prefixer(prefix):
    def add_prefix(text):
        return f"{prefix}: {text}"
    return add_prefix

warn = make_prefixer("WARNING")
print(warn("System alert"))
