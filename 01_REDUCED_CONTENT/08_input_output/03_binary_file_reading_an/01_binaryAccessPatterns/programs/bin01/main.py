path = "chunk_read_demo.bin"
data = b"Chunk1\nChunk2\nChunk3\n"
with open(path, "wb") as f:
    f.write(data)
with open(path, "rb") as f:
    while chunk := f.read(8):
        print(repr(chunk))
