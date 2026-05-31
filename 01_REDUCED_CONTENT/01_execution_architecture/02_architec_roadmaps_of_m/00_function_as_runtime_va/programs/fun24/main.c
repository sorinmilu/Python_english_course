#include <stdio.h>

typedef void (*event_callback_t)(int event_code, void *user_data);

void dispatch_event(event_callback_t callback, void *user_data) {
    int event_code = 42;
    callback(event_code, user_data);
}

void print_event(int event_code, void *user_data) {
    const char *name = (const char *)user_data;
    printf("%s received event %d\n", name, event_code);
}

int main(void) {
    dispatch_event(print_event, "handler A");
    return 0;
}
