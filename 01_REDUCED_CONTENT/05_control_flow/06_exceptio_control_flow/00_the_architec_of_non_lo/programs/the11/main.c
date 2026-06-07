/* C-style idea, not Python */
FILE *fp = fopen("data.txt", "r");

if (fp == NULL) {
    printf("could not open file\n");
    return 1;
}

read_from_file(fp);
fclose(fp);
