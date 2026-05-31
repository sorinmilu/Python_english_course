def make_default_tag():
    print("make_default_tag() running")
    return "D'oh!"

def show_tag(text=make_default_tag()):
    return text

show_tag()
show_tag("other")
