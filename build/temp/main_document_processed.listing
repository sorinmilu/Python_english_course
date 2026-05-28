struct connection {
    int fd;
    char input_buffer[4096];
    size_t input_used;
    void (*on_readable)(struct connection *);
};

while (1) {
    wait_for_ready_file_descriptors();

    for each ready connection:
        connection->on_readable(connection);
}
