---
description: Build the artifact and read what the build actually says
argument-hint: [spec directory]
---

Load the `module-compile` skill and follow it for the module at $ARGUMENTS (ask if not given). `--strict` is a determinism gate, not a correctness gate — do not report a clean strict compile as evidence the module is right.

The skill is the procedure; this command only routes to it. Do not restate `module-compile`'s content here or work from memory of it — load it.
