import dis

def local_access(name, score):
    message = f"{name}: {score}"
    return message

def global_access():
    return answer

answer = 42

dis.dis(local_access)
print("---")
dis.dis(global_access)
