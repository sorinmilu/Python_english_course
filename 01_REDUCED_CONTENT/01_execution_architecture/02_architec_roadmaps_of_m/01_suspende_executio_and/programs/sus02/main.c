#include <stdio.h>

struct generator {
    int state;
    int i;
};

int gen_next(struct generator *g, int *out) {
    switch (g->state) {
        case 0:
            g->i = 1;

        case 1:
            if (g->i <= 3) {
                *out = g->i;
                g->i += 1;
                g->state = 1;
                return 1;
            }

            g->state = 2;

        case 2:
            return 0;
    }

    return 0;
}
