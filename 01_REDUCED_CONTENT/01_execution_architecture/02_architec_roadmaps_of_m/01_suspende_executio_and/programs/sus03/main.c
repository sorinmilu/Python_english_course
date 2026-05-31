#include <stdio.h>

struct counter {
    int current;
    int limit;
};

int counter_next(struct counter *c, int *out) {
    if (c->current > c->limit) {
        return 0;
    }

    *out = c->current;
    c->current += 1;
    return 1;
}

int main(void) {
    struct counter c = { .current = 1, .limit = 3 };

    int value;
    while (counter_next(&c, &value)) {
        printf("%d\n", value);
    }

    return 0;
}
