count_up_to(3)
    creates generator object
    body has not run yet

next(g)
    creates/resumes generator frame
    current = 1
    reaches yield current
    returns 1 and suspends

next(g)
    resumes after yield
    current += 1
    reaches yield current
    returns 2 and suspends
