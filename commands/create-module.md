---
description: Make a just-dna module — find the right entry point, then run the stage that owns it
argument-hint: [a trait, gene, sources, or a spec directory]
---

Load the `create-module` skill and route: $ARGUMENTS

Work out where the author is actually standing before starting anything. A spec directory that has been here before is a second pass, and entering it as a first pass re-derives work already on disk — `module-revise` owns that case, and `module-status` reads a directory whose state nobody knows.

The skill is the router and each stage skill is the procedure; this command only routes to it. Do not restate `create-module`'s content here or work from memory of it — load it.
