# AIR intrinsics

An inventory and argument reference for Apple's Metal intermediate representation, with small compiler probes and GPU execution samples. Extracted from Apple Metal compiler 32023.883.

## Argument reference

Start with **[AIR-ARGUMENTS.md](AIR-ARGUMENTS.md)**. It has a row for every extracted intrinsic base, including:

- Observed parameter types, their order and return types.
- Links to source examples where available.
- Candidate conversion inputs inferred from name tokens, explicitly distinguished from verified signatures.
- Unresolved contracts where the available evidence does not establish what can be passed.

[AIR-ARGUMENTS.json](AIR-ARGUMENTS.json) contains exact declarations, individual overloads and recorded kernel inputs. Kernel inputs are not necessarily the intrinsic's direct operands: inspect the linked source for intermediate values, resource handles and control arguments.

Current argument coverage across all extracted versions:

| Evidence | Base names |
|---|---:|
| Observed compiler signatures | 368 |
| Name-inferred conversion candidates, no observed signature | 5,971 |
| Argument contract unresolved | 11,778 |

This is not yet a complete calling-contract specification. No valid arguments are invented for unresolved entries.

## Inventory and execution coverage

- 18,116 intrinsic base names in AIR 2.8.
- 18,117 unique names across 12 embedded version tables.
- 338 kernel samples passed their output checks.
- Those kernels contain 573 typed AIR symbols mapping to 353 base names.
- 17,763 AIR 2.8 bases remain untested on the GPU. Async-copy/event operations are not GPU-tested.

A passing sample does not establish every overload, exceptional value, precision rule or memory-ordering behavior. Some successful cast kernels emit no AIR call and receive no intrinsic coverage credit.

## Files

| File or directory | Contents |
|---|---|
| `AIR-ARGUMENTS.md` / `.json` | Argument reference, evidence labels and source examples |
| `AIR-2.8-INTRINSICS.txt` | Current-version base names, one per line |
| `AIR-INTRINSICS.md` / `.json` | Version membership, IDs, overload flags and observations |
| `AIR-ALL-VERSIONS-INTRINSICS.txt` | Union of all extracted version tables |
| `AIR-OBSERVED-SIGNATURES.json` | Original compile-probe declarations |
| `GPU-COVERAGE.md` / `.json` | Per-base execution coverage |
| `GPU-RESULTS.json` | Recorded inputs, expected/actual outputs and declarations |
| `evidence/tables/tables.json` | Extracted name/type-table data and offsets |
| `probes/`, `runtime/`, `evidence/` | Source examples and retained source snapshots |
| `tools/` | Extraction, generation, compilation and execution scripts |
| `tests/` | Offline consistency and source-generation tests |

The recorded results are a selected projection of the experiment evidence, not a full raw capture. Compiled artifacts and full execution logs are not included. Source hashes verify the included example bytes; the file manifest verifies the distributed files.

## Offline verification

Python 3.9+ standard library only. The default suite does not invoke a GPU or compiler:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Regenerate the argument reference:

```sh
python3 tools/arguments.py
```

## Run examples locally

Requires an existing compatible Apple Metal toolchain and Swift compiler. Review each source and its expected outputs first.

Compile the original probes:

```sh
python3 tools/probe_runner.py --evidence local-output/compile --budget 60
```

Execute the original 21 small GPU cases:

```sh
python3 tools/run_gpu.py --limit 21 --output local-output/gpu --budget 90
```

Additional suites: `--suite conversions --limit 300`, `--suite atomics --limit 5`, and `--suite extended-math --limit 12`. Choose a new output directory for each run.

The runtime checks thermal state and stops on errors or mismatches. Dispatches are small and fixed, but a process timeout cannot reliably cancel already-submitted GPU work. Do not use the runner as a sandbox for arbitrary shaders or guessed AIR declarations.

## Acknowledgements

- **[Hermes Agent](https://hermes-agent.nousresearch.com/docs)** by Nous Research assisted with research, tool development, experiment orchestration and validation.
- **[REA — Reverse Engineer Anything](https://github.com/morluto/rea)** provided workflow and evidence-provenance guidance through its repository documentation. REA's CLI/MCP engine was not executed for these results; extraction and testing used Apple's tools and the scripts included here.

These acknowledgements do not imply endorsement or independent verification by either project.
