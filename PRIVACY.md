# Privacy boundary

This release includes only selected UTF-8 research data, Python/Swift/Metal source and documentation. It was constructed separately from the original local evidence; no history, credentials or machine environment was copied.

Removed or excluded:
- Personal home paths and original workspace location.
- Host device name, OS version/build, SDK installation paths and mounted-toolchain paths.
- Command invocations and logs carrying local paths.
- Timing/thermal observations and raw host environment reports.
- Executables, AIR bitcode, LLVM text, metallibs and raw buffer files.
- Private snapshots of Git configuration, remotes, authors or history.

Preserved:
- Public compiler version and compiler-binary digest for version-specific claims.
- Intrinsic names, version-local IDs, type-table raw words and static offsets.
- Original small source examples and their hashes.
- Numeric GPU sample inputs/expected/actual outputs, with identifying execution context removed.
- Explicit gaps: most intrinsic bases remain untested; this is not a full specification.

Evidence JSON was projected or sanitized; it is not the original raw record. Export hashes are computed over sanitized bytes. Generic platform strings in code and test fixtures are not a claim about the originating computer.

Validation scans cover content, filenames and Git-local metadata. Pattern scans cannot prove the absence of every possible secret. Review the Git diff before any public push. New compiler/runtime runs can write your own local paths; output should remain under `local-output/` until separately reviewed.

No commits were created, so no author identity or email was added to history. A future GitHub repository is associated with its owner account, and future commits can expose configured author name/email; use GitHub's no-reply email if desired.
