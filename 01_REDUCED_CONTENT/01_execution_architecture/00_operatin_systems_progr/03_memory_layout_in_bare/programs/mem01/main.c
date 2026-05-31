/* main.c */
extern int shared_counter;

int main(void) {
    shared_counter++;
    return 0;
}
