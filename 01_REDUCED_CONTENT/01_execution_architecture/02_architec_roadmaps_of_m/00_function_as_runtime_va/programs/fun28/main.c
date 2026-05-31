#include <stdio.h>

int factor = 3;

int (^multiply)(int) = ^int(int value) {
    return value * factor;
};

int main(void) {
    printf("%d\n", multiply(10));
    return 0;
}
