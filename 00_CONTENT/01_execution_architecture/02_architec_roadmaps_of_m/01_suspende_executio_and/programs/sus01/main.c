#include <stdio.h>

struct task {
    const char *name;
    int state;
    int current;
    int limit;
};

int task_step(struct task *t) {
    switch (t->state) {
        case 0:
            t->current = 0;
            t->state = 1;

        case 1:
            if (t->current < t->limit) {
                printf("%s %d\n", t->name, t->current);
                t->current++;
                return 1;
            }

            t->state = 2;

        case 2:
            return 0;
    }

    return 0;
}

int main(void) {
    struct task a = {"A", 0, 0, 3};
    struct task b = {"B", 0, 0, 3};

    while (task_step(&a) | task_step(&b)) {
        /* keep stepping while either task can run */
    }

    return 0;
}
