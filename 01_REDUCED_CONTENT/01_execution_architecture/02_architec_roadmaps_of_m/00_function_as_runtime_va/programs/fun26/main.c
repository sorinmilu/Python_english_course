struct closure bad_make_multiplier(int factor) {
    struct multiplier_env env;
    env.factor = factor;

    struct closure c;
    c.call = multiply_call;
    c.env = &env;  /* invalid after return */

    return c;
}
