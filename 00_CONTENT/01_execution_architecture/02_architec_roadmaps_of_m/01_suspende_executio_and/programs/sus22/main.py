caller asks for next value
    generator frame resumes
        runs until yield
        produces value
        suspends
caller receives value

caller asks again
    same generator frame resumes after previous yield
        runs until next yield
        produces value
        suspends again
