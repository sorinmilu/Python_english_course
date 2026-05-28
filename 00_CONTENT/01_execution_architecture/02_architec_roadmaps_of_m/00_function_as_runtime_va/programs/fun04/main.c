typedef int (*operation_t)(int value, void *context);

int apply(int value, operation_t operation, void *context) {
    return operation(value, context);
}

struct multiplier {
    int factor;
};

int multiply_by(int value, void *context) {
    struct multiplier *m = context;
    return value * m->factor;
}

int main(void) {
    struct multiplier m = { .factor = 3 };
    int result = apply(10, multiply_by, &m);
    return 0;
}
