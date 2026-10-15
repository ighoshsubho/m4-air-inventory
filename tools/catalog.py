"""Offline AIR evidence extraction; string presence is not intrinsic validation."""
import re
import struct
import hashlib
import mmap
from pathlib import Path


CANDIDATE = re.compile(rb"(?:\A|(?<=\x00))(air\.[A-Za-z0-9_.]+)(?=\x00)")


def candidates(data):
    return [(match[1].decode("ascii"), match.start(1)) for match in CANDIDATE.finditer(data)]


def cstring_sections(data):
    def check(offset, size, end):
        if offset < 0 or size < 0 or offset + size > end:
            raise ValueError("Mach-O range exceeds file or slice")

    check(0, 8, len(data))
    magic, count = struct.unpack_from(">II", data)
    if magic == 0xcafebabe:
        check(8, count * 20, len(data))
        slices = []
        for i in range(count):
            cpu, _, start, size, _ = struct.unpack_from(">5I", data, 8 + i * 20)
            check(start, size, len(data))
            if cpu == 0x100000c:
                slices.append((start, size))
    else:
        slices = [(0, len(data))]
    result = []
    for base, size in slices:
        end = base + size
        check(base, 32, end)
        magic, cpu, _, _, ncmds, cmdbytes, _, _ = struct.unpack_from("<8I", data, base)
        if magic != 0xfeedfacf or cpu != 0x100000c:
            raise ValueError("Expected little-endian arm64 Mach-O")
        cursor = base + 32
        check(cursor, cmdbytes, end)
        commands_end = cursor + cmdbytes
        for _ in range(ncmds):
            check(cursor, 8, commands_end)
            command, length = struct.unpack_from("<II", data, cursor)
            if length < 8:
                raise ValueError("Invalid load command size")
            check(cursor, length, commands_end)
            if command == 0x19:
                check(cursor, 72, cursor + length)
                segment = struct.unpack_from("<II16sQQQQiiII", data, cursor)
                sections = segment[-2]
                check(cursor + 72, sections * 80, cursor + length)
                for j in range(sections):
                    values = struct.unpack_from("<16s16sQQIIIIIIII", data, cursor + 72 + j * 80)
                    name, segname, _, section_size, offset = values[:5]
                    if name.rstrip(b"\0") == b"__cstring":
                        check(base + offset, section_size, end)
                        result.append({"architecture": "arm64", "section": segname.rstrip(b"\0").decode() + ",__cstring", "offset": base + offset, "size": section_size})
            cursor += length
    if not result:
        raise ValueError("No arm64 C-string section found")
    return result


def extract_file(path):
    path = Path(path).resolve()
    with path.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            digest = hashlib.sha256(data).hexdigest()
            sections = cstring_sections(data)
            names = {}
            for section in sections:
                start = section["offset"]
                for name, offset in candidates(data[start:start + section["size"]]):
                    names.setdefault(name, []).append(start + offset)
            return {"path": str(path), "size": len(data), "sha256": digest,
                    "sections": sections, "names": names}


def main():
    import argparse
    import json
    import subprocess
    import time

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = None
    if args.paths:
        paths = sorted({Path(p).resolve() for p in args.paths})
    else:
        resource = subprocess.check_output(["xcrun", "metal", "-print-resource-dir"], text=True, timeout=20).strip()
        root = Path(resource).parents[2]
        paths = sorted({p.resolve() for p in root.rglob("*") if p.is_file()
                        and (p.suffix == ".dylib" or (p.parent == root / "bin" and p.stat().st_size > 1000000))})
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "strings").mkdir(exist_ok=True)
    files, union = [], {}
    for i, path in enumerate(paths):
        started = time.monotonic()
        label = str(path.relative_to(root)) if root else str(path)
        record = {"path": str(path), "relative": label}
        try:
            result = extract_file(path)
            target = args.output / "strings" / (str(i) + ".json")
            target.write_text(json.dumps(result, indent=2) + "\n")
            record.update({"evidence": str(target), "names": len(result["names"]), "sha256": result["sha256"], "size": result["size"]})
            for name, offsets in result["names"].items():
                union.setdefault(name, []).append({"file": label, "offsets": offsets})
        except (ValueError, OSError) as error:
            record["error"] = str(error)
        record["elapsed_seconds"] = time.monotonic() - started
        files.append(record)
        (args.output / "scan-manifest.json").write_text(json.dumps({"root": str(root) if root else None, "files": files}, indent=2) + "\n")
    (args.output / "all-candidates.json").write_text(json.dumps(union, indent=2, sort_keys=True) + "\n")
    (args.output / "AIR-ALL-CANDIDATES.txt").write_text("# Exact air.* C-string candidates; NOT all confirmed intrinsics.\n" + "\n".join(sorted(union)) + "\n")
    print(json.dumps({"files": len(files), "failed_files": sum("error" in f for f in files), "unique_candidates": len(union)}))


if __name__ == "__main__":
    main()
