# AIR intrinsic inventory and bounded GPU samples

Privacy-filtered research snapshot for Apple Metal compiler 32023.883, AIR 2.8. Not affiliated with or endorsed by Apple. This is a name inventory and experimental tooling, not a complete AIR specification or conformance suite.

## Results

- 18,116 intrinsic base names in the extracted AIR 2.8 table.
- 18,117 unique base names across 12 embedded version tables.
- 338 previously executed GPU kernel samples passed their output checks.
- 573 typed AIR calls, mapping to 353 base names, occur in those passing kernels.
- 17,763 base names remain untested. Async-copy/event operations are not GPU-tested.

A passing sample does not prove all types, operands, exceptional values, precision guarantees, memory ordering or retention of the same operation after GPU optimization. Some passing cast kernels emit no AIR call; they receive no intrinsic coverage credit.

## Contents

- `AIR-2.8-INTRINSICS.txt`: complete current-version base-name list.
- `AIR-INTRINSICS.md` / `.json`: annotated inventory, version-local IDs, overload flags and compile-only observations.
- `AIR-ALL-VERSIONS-INTRINSICS.txt`: union of extracted version tables.
- `AIR-OBSERVED-SIGNATURES.json`: declarations observed in the original compile-only corpus.
- `GPU-COVERAGE.md` / `.json`: explicit per-base GPU sample status.
- `GPU-RESULTS.json`: privacy-filtered recorded expected/actual outputs and emitted declarations.
- `evidence/tables/tables.json`: static table data and offsets; local compiler paths/commands removed.
- `probes/` and `runtime/*-sources/`: original Metal examples and generated bounded sources.
- Other `.metal` files under `runtime/` and `evidence/`: original source snapshots corresponding to historical observations. No compiled code is included.
- `tools/`: extraction, compilation, generation and opt-in GPU execution scripts.
- `tests/`: offline consistency/privacy and source-generation tests.

## Privacy and evidence transformation

This is a new repository with no imported Git history. The original private evidence directory was not changed. Home-directory names, absolute local paths, OS/build details, device names, thermal readings and execution timings have been omitted. No raw compiler logs, environment report, AIR/LLVM-IR files, metallibs, executables, raw buffer dumps or credentials are distributed.

Compiler version, target-type declarations, generic source code, compiler-binary SHA-256, table offsets and artifact-independent facts remain for scientific provenance. The compiler hash identifies a toolchain build, not a person. Target names inside runnable code or unit fixtures describe APIs/platforms, not personal machine records.

`GPU-RESULTS.json` is an explicitly transformed projection, not untouched raw evidence. Actual/expected numeric outputs and source bytes are preserved. Source hashes are checked against the included files. Removed binaries cannot be revalidated from this export. `RELEASE-MANIFEST.json` hashes exported bytes, not the original private bundle. See `PRIVACY.md`.

## Offline verification

Python 3.9+ standard library only; no GPU or compiler is invoked by this default suite:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

## Optional local reproduction

Requires an existing compatible Apple Metal toolchain and Swift compiler. No installers are provided. Review source and expected outputs before execution. The table extractor is version/layout-specific, not a general hostile-input parser.

Compile-only baseline, writing to an ignored local directory:

```sh
python3 tools/probe_runner.py --evidence local-output/compile --budget 60
```

Opt-in GPU execution of the original 21 small cases:

```sh
python3 tools/run_gpu.py --limit 21 --output local-output/gpu --budget 90
```

Extra suites: `--suite conversions --limit 300`, `--suite atomics --limit 5`, or `--suite extended-math --limit 12`. Use a new output directory for each run. Generated conversion/atomic sources are included; their generator functions are also available in `tools/conversion_cases.py` and `tools/atomic_cases.py`.

The runtime stops on errors or mismatches, checks thermal state, and uses small fixed dispatches. A process timeout cannot reliably cancel GPU work already submitted. This is not a sandbox or a zero-risk guarantee. The scripts use local absolute paths in newly generated evidence: do not publish a fresh run without another privacy export and audit. Default ignored extensions/directories reduce accidental staging but do not replace review.

## Acknowledgements

- **[Hermes Agent](https://hermes-agent.nousresearch.com/docs)** by Nous Research assisted with research, tool development, experiment orchestration, validation and preparation of the privacy-filtered release.
- **[REA — Reverse Engineer Anything](https://github.com/morluto/rea)** provided workflow and evidence-provenance guidance through its repository documentation. REA's CLI/MCP analysis engine was not executed for these results; extraction and testing used Apple's tools and the scripts included here.

These acknowledgements do not imply endorsement or independent verification by either project.

## Publication and licensing

No license has been chosen on the owner's behalf. See `PUBLICATION.md` before distributing. Apple compiler binaries and headers are not included. Public hosting alone does not grant an open-source license. This repository has not been uploaded, committed or pushed by the export process.
