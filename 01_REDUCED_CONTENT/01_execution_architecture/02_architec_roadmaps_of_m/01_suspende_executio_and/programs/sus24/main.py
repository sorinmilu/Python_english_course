def non_empty_lines(path):
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line:
                yield line


for line in non_empty_lines("log.txt"):
    print(line)
