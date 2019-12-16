typedef struct {
    char c;
    const char* str;
} cli_flag_t;

typedef enum {
    ARG_TYP_FLAG = 0,
    ARG_TYP_INT,
    ARG_TYP_STR,
    ARG_TYP_CALLBACK
} cli_arg_type_t;

typedef struct {
    char flag;
    const char* desc;
    const char* usage;
    struct {
        int required;
        int has_value;
    } opts;
    void* set;
    cli_arg_type_t type;
    int _present;
} cli_cmd_t;


void cli_help(char* const argv[], const char* prog_desc, const char* cmds, const char* cmd_desc[])
{
    int cmd_idx = 0;
    printf("%s\n", argv[0]);
    printf("%s\n", (prog_desc));
    for (int i = 0; i < strlen((cmds)); i++)
    {
        const char* desc = (cmd_desc)[cmd_idx];
        if ((cmds)[i] == ':') continue;
        if (cmds[i] == 'h') desc = "Show this help";
        printf("-%c\t%s\n", (cmds)[i], desc);
        cmd_idx++;
    }
    exit(0);
}


int cli(
    const char* prog_desc,
    cli_cmd_t cmds[],
    int argc,
    char* const argv[]
)
{
    int res = 0, num_cmds = 0;
    for (; cmds[num_cmds].flag; num_cmds++);

    // allocate and build the argument string
    char* arg_str = (char*)calloc((num_cmds + 1) * 2, sizeof(char));
    if (!arg_str) { res = -1; goto done; } // escape on allocation failure
    for(int s = 0, i = num_cmds; i--;)
    {
        const char* fstr = cmds[i].opts.has_value ? "%c:" : "%c";
        s += sprintf(arg_str + s, fstr, cmds[i].flag);
    }

    arg_str[strlen(arg_str)] = 'h';

    // process
    int c;
    while ((c = getopt(argc, argv, arg_str)) != -1)
    for (int i = num_cmds; i--;)
    {
        cli_cmd_t* cmd = cmds + i;

        if (c == 'h')
        {
            const char* cmd_descs[num_cmds];
            for (int i = num_cmds; i--;) { cmd_descs[(num_cmds - 1) - i] = cmds[i].desc; }
            cli_help(argv, prog_desc, arg_str, cmd_descs);
        }
        else if (cmd->flag == c)
        {
            cmd->_present = 1;
            switch(cmd->type)
            {
                case ARG_TYP_FLAG:
                    *((int*)cmd->set) = 1;
                    break;
                case ARG_TYP_INT:
                    *((int*)cmd->set) = atoi(optarg);
                    break;
                case ARG_TYP_STR:
                {
                    char** str = (char**)cmd->set;
                    int len = strlen(optarg);
                    *str = (char*)calloc(len + 1, sizeof(char));
                    if (!*str)
                    {
                        res = -(10 + i);
                        goto done;
                    }
                    strncpy(*str, optarg, len);
                } break;
                case ARG_TYP_CALLBACK:
                    res = ((int(*)(char,const char*))cmd->set)(c, optarg);
                    if (res) { goto done; }
                    break;
            }
        }
    }

    // check that all required options are fulfilled
    for (int i = num_cmds; i--;)
    {
        cli_cmd_t* cmd = cmds + i;

        if (cmd->opts.required && !cmd->_present)
        {
            fprintf(stderr, "Missing required %s -%c for %s\n",
                cmd->opts.has_value ? "parameter" : "flag",
                cmd->flag,
                cmd->desc
            );
            res = -2;
        }
    }

done:
    free(arg_str);
    return res;
}
