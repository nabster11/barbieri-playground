#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>

static const char DEV[] = "/sys/class/leds/smc::kbd_backlight/brightness";

static void usage(const char *prog)
{
    fprintf(stderr, "Usage:\n\t%s [-step|+step|=value]\n", prog);
}

int main(int argc, char *argv[])
{
    int old, new;
    FILE *f = fopen(DEV, "rb");

    if (!f) {
        fprintf(stderr, "could not open for reading '%s': %s\n", DEV, strerror(errno));
        return 1;
    }

    if (fscanf(f, "%d", &old) != 1) {
        fprintf(stderr, "could not read integer from '%s': %s\n", DEV, strerror(errno));
        fclose(f);
        return 1;
    }
    fclose(f);

    if (argc < 2) new = (old + 32) % 256;
    else if (argc != 2) {
        usage(argv[0]);
        return 2;
    } else if (strcmp(argv[1], "-h") == 0) {
        usage(argv[0]);
        return 0;
    } else {
        switch (argv[1][0]) {
        case '-': new = old - atoi(argv[1] + 1); break;
        case '+': new = old + atoi(argv[1] + 1); break;
        case '=': new = atoi(argv[1] + 1); break;
        default:
            fprintf(stderr, "invalid action '%c' for parameter '%s'.\n", argv[1][0], argv[1]);
            usage(argv[0]);
            return 2;
        }
    }

    if (new < 0) new = 0;
    else if (new > 255) new = 255;

    f = fopen(DEV, "wb");
    if (!f) {
        fprintf(stderr, "could not open for writing '%s': %s\n", DEV, strerror(errno));
        return 1;
    }

    fprintf(f, "%d", new);
    fclose(f);

    return 0;
}
