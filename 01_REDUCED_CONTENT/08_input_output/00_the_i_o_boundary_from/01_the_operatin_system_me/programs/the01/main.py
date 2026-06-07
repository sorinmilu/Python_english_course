import os
import sys

stdout_obj = sys.stdout
stdout_fd = stdout_obj.fileno()
print(stdout_obj, stdout_fd, type(stdout_fd))

text = "Chuck Norris counted to infinity. Twice.\n"
data = text.encode("utf-8")
os.write(stdout_fd, data)
sys.stdout.flush()
