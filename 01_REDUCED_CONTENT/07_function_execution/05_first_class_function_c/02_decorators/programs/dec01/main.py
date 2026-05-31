@make_logged
def shout(text):
    return text.upper()

# equivalent to:
def shout(text):
    return text.upper()
shout = make_logged(shout)
