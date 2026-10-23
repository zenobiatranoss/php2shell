# php2shell

this repository is basically a collection of tools and scripts focused on low-level php exploitation, memory manipulation, and heap spraying. it dives deep into how php handles sessions, specifically looking at things like session upload progress, memory leaks, and how to turn low-level bugs into full remote code execution.

## what this project is about

if you ever wondered how people mess with php internals from the network layer, this project is a playground for that. it avoids high-level web frameworks and talks straight to the target using raw sockets and custom http requests. we deal with things like chunked transfer encoding, multipart form data building, and manipulating heap layouts to hijack execution pointers.

## how the exploit works

the exploitation process in this project isn't just a simple one-shot request. it's broken down into multiple carefully timed stages:

- **worker stabilization and rotation:** before doing anything heavy, the scripts send a bunch of big payloads to clear or reset php workers and stabilize the heap environment.
- **stage 1 (chunk base leak):** by sending specially crafted inputs and reading back cookie data, the script uses statistical counters to figure out where the heap chunks are located in memory.
- **stage 2 (libphp base leak):** next, it looks for specific pointer dtor offsets to calculate the exact base address of the loaded library in memory.
- **stage 3 (fake structures and triggering):** once it knows where everything is, it builds fake hash tables and memory structures, sprays them, and triggers the vulnerability to force php into calling system functions like `zif_system` with whatever command we want.

## the auditing script (matrix_audit.py)

we also added an auditing tool called `matrix_audit.py` inside the exploit folder. instead of blindly trying to exploit a live target, this script acts as a deep compatibility and vulnerability checker. it runs low-level socket connections, tests if the target handles large multipart data correctly, checks for upload progress behavior, and looks for error signatures that tell you if the environment is vulnerable or properly patched.

## how to run stuff

to run the auditor script against a target url, you can use python directly from the project root. make sure you point it to the right path inside the exploit folder:

python3 exploit/matrix_audit.py -u http://localhost/target.php

if you want to run other scripts like the pure offset exploit or the automated local tester, you can check them out as well. for example, the auto runner can be executed with:

python3 exploit/auto_exp.py --cmd "id > /tmp/proof"

## setting up the lab

to test this safely, you usually want to spin up a local php docker container or a specific version of php where these behaviors are reproducible. the scripts have profiles built-in for things like bookworm or custom lab environments so you can tweak offsets depending on your local binary symbols using tools like nm or readelf.

that's pretty much it. everything is built to be raw, low-level, and educational for understanding php internals and memory safety issues.