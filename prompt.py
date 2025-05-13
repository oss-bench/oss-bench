class Prompt:
    system_prompt = "You are an expert on C programming."
    optimizing_prompt = "Please optimize the following C function snippet (dont add header files) and (1) ensure memory safety (2) improve code efficiency. Give the optimized code directly without explanation. \nThe code is as following:\n```c\n{cfunction}\n```\n"
