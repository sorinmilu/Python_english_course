#include <stdio.h>
#include <stdlib.h>

int compare_ints(const void *left, const void *right) {
    int a = *(const int *)left;
    int b = *(const int *)right;

    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
}

int main(void) {
    int values[] = {4, 1, 3, 2};
    size_t count = sizeof(values) / sizeof(values[0]);

    qsort(values, count, sizeof(values[0]), compare_ints);

    for (size_t i = 0; i < count; i++) {
        printf("%d\n", values[i]);
    }

    return 0;
}
