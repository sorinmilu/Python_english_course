#include <sys/select.h>
#include <unistd.h>
#include <stdio.h>

void handle_stdin(void) {
    char buffer[256];
    ssize_t n = read(STDIN_FILENO, buffer, sizeof(buffer) - 1);

    if (n > 0) {
        buffer[n] = '\0';
        printf("input: %s", buffer);
    }
}

int main(void) {
    while (1) {
        fd_set read_set;

        FD_ZERO(&read_set);
        FD_SET(STDIN_FILENO, &read_set);

        int max_fd = STDIN_FILENO;

        select(max_fd + 1, &read_set, NULL, NULL, NULL);

        if (FD_ISSET(STDIN_FILENO, &read_set)) {
            handle_stdin();
        }
    }

    return 0;
}
