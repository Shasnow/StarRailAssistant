#include <stdlib.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char const *argv[])
{
    const char *base_cmd = "python\\python.exe SRA\\main.py";

    int total_len = strlen(base_cmd);
    for (int i = 1; i < argc; i++)
    {
        total_len += strlen(argv[i]) + 1;
    }
    total_len += 1;

    char *full_cmd = (char *)malloc(total_len);
    if (full_cmd == NULL)
    {
        printf("malloc error\n");
        return 1;
    }

    strcpy(full_cmd, base_cmd);

    for (int i = 1; i < argc; i++)
    {
        strcat(full_cmd, " ");
        strcat(full_cmd, argv[i]);
    }

    int ret = system(full_cmd);

    free(full_cmd);

    if (ret == -1)
    {
        printf("Failure\n");
        return 1;
    }
    return 0;
}