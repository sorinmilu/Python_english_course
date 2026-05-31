#include <stdio.h>
#include <stdlib.h>

typedef int (*call_fn)(void *env, int value);

struct closure {
    call_fn call;
    void *env;
};

struct multiplier_env {
    int factor;
};

int multiply_call(void *env, int value) {
    struct multiplier_env *m = env;
    return value * m->factor;
}

struct closure make_multiplier(int factor) {
    struct multiplier_env *env = malloc(sizeof(*env));
    env->factor = factor;

    struct closure c;
    c.call = multiply_call;
    c.env = env;

    return c;
}

void destroy_multiplier(struct closure c) {
    free(c.env);
}

int main(void) {
    struct closure times_three = make_multiplier(3);

    printf("%d\n", times_three.call(times_three.env, 10));

    destroy_multiplier(times_three);
    return 0;
}
