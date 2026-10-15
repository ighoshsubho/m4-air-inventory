"""Static, fail-closed extraction of the installed compiler's AIR name tables."""
import re


def decode_rebase(value):
    if value >> 63 or ((value >> 44) & 0x7f):
        raise ValueError("Expected a format-6 rebase, not a bind or reserved bits")
    target = value & ((1 << 36) - 1)
    high8 = (value >> 36) & 0xff
    if high8:
        raise ValueError("Unexpected high8 in local image rebase")
    return 0x100000000 + target, ((value >> 51) & 0xfff) * 4


def constructor_arguments(text):
    registers = {}
    for line in text.splitlines():
        if re.search(r"\bbl\s", line):
            break
        match = re.search(r"adrp\s+x(\d+),.*; (0x[0-9a-f]+)", line)
        if match:
            registers[int(match[1])] = int(match[2], 16)
        match = re.search(r"add\s+x(\d+),\s*x(\d+),\s*#(0x[0-9a-f]+|\d+)", line)
        if match and int(match[2]) in registers:
            registers[int(match[1])] = registers[int(match[2])] + int(match[3], 0)
        match = re.search(r"mov\s+w(\d+),\s*#(0x[0-9a-f]+|\d+)", line)
        if match:
            registers[int(match[1])] = int(match[2], 0)
    if not all(i in registers for i in range(2, 8)):
        raise ValueError("Unrecognized constructor: required table arguments missing")
    if registers[5] != registers[3] + 1:
        raise ValueError("Name and type-table counts are inconsistent")
    return registers


def main():
    import argparse
    import hashlib
    import json
    import mmap
    import struct
    import subprocess
    import threading
    from pathlib import Path
    from catalog import cstring_sections

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(subprocess.check_output(["xcrun", "metal", "-print-resource-dir"], text=True, timeout=20).strip()).parents[2]
    path = root / "bin/metal"
    symbols = subprocess.check_output(["nm", "-arch", "arm64", str(path)], text=True, timeout=20)
    constructors = re.findall(r"([0-9a-f]+) T (\S*AIRFunctionInfo(\d+d\d+)C1E\S*)", symbols)
    if not constructors:
        raise ValueError("No versioned AIR constructors found")
    with path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
        sections = cstring_sections(data)
        magic, count = struct.unpack_from(">II", data)
        if magic != 0xcafebabe:
            raise ValueError("Expected installed universal compiler")
        slices = [struct.unpack_from(">5I", data, 8 + i * 20) for i in range(count)]
        arm = [s for s in slices if s[0] == 0x100000c]
        if len(arm) != 1:
            raise ValueError("Expected exactly one arm64 slice")
        base, size = arm[0][2:4]
        ncmds = struct.unpack_from("<I", data, base + 16)[0]
        cursor = base + 32
        segments, fixups = [], None
        for _ in range(ncmds):
            command, length = struct.unpack_from("<II", data, cursor)
            if command == 0x19:
                seg = struct.unpack_from("<II16sQQQQiiII", data, cursor)
                segments.append({"name": seg[2].rstrip(b"\0").decode(), "vm": seg[3], "vmsize": seg[4], "offset": seg[5], "size": seg[6]})
            elif command == 0x80000034:
                fixups = struct.unpack_from("<II", data, cursor + 8)
            cursor += length
        if not fixups or not any(s["name"] == "__TEXT" and s["vm"] == 0x100000000 for s in segments):
            raise ValueError("Unsupported image layout or missing chained fixups")

        def at(va, length=1):
            for seg in segments:
                if seg["vm"] <= va and va + length <= seg["vm"] + seg["size"]:
                    return base + seg["offset"] + va - seg["vm"]
            raise ValueError("Address is not in a file-backed segment")

        fixbase = base + fixups[0]
        fixend = fixbase + fixups[1]
        if fixend > base + size:
            raise ValueError("Fixups exceed slice")
        version, starts_offset = struct.unpack_from("<II", data, fixbase)
        if version != 0:
            raise ValueError("Unsupported fixup version")
        starts = fixbase + starts_offset
        segcount = struct.unpack_from("<I", data, starts)[0]
        locations = set()
        for i in range(segcount):
            relative = struct.unpack_from("<I", data, starts + 4 + 4 * i)[0]
            if not relative:
                continue
            pos = starts + relative
            length, page_size, fmt, segment_offset, _, pages = struct.unpack_from("<IHHQIH", data, pos)
            if fmt != 6 or pos + length > fixend or 22 + 2 * pages > length:
                raise ValueError("Unsupported chained-fixup segment")
            for page in range(pages):
                start = struct.unpack_from("<H", data, pos + 22 + 2 * page)[0]
                if start == 0xffff:
                    continue
                if start & 0x8000:
                    raise ValueError("Multi-start pages not supported")
                offset = segment_offset + page * page_size + start
                page_end = segment_offset + (page + 1) * page_size
                while True:
                    if offset + 8 > size or offset + 8 > page_end or offset in locations:
                        raise ValueError("Invalid or cyclic fixup chain")
                    locations.add(offset)
                    word = struct.unpack_from("<Q", data, base + offset)[0]
                    step = ((word >> 51) & 0xfff) * 4
                    if not step:
                        break
                    offset += step

        result = {"compiler_path": str(path), "compiler_sha256": hashlib.sha256(data).hexdigest(), "arm64_slice_offset": base, "registered_fixup_locations": len(locations), "pointer_format": 6, "versions": {}}
        def disassemble(symbol):
            command = ["otool", "-arch", "arm64", "-tvV", "-p", symbol, str(path)]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            timer = threading.Timer(15, process.kill)
            timer.start()
            lines = []
            try:
                for line in process.stdout:
                    lines.append(line)
                    if re.search(r"\bret\s*$", line):
                        break
                    if len(lines) > 80:
                        raise ValueError("Function did not end within 80 lines")
            finally:
                process.terminate()
                process.communicate(timeout=10)
                timer.cancel()
            if not lines or not re.search(r"\bret\s*$", lines[-1]):
                raise ValueError("Incomplete bounded disassembly")
            return command, "".join(lines)

        for _, symbol, tag in sorted(constructors, key=lambda item: tuple(map(int, item[2].split("d")))):
            command, text = disassemble(symbol)
            (args.output / (tag + "-constructor.txt")).write_text(text)
            regs = constructor_arguments(text)
            overload_symbol = re.search(r"\S+AIRFunctionInfo" + tag + r"12isOverloadedEj", symbols).group(0)
            _, overload_text = disassemble(overload_symbol)
            (args.output / (tag + "-overloads.txt")).write_text(overload_text)
            page = re.search(r"adrp\s+x9,.*; (0x[0-9a-f]+)", overload_text)
            add = re.search(r"add\s+x9,\s*x9,\s*#(0x[0-9a-f]+|\d+)", overload_text)
            if not page or not add or not re.search(r"lsr\s+x8,\s*x8,\s*#3", overload_text):
                raise ValueError("Unsupported overload-bitset accessor")
            overload_va = int(page[1], 16) + int(add[1], 0)
            overload_offset = at(overload_va, (regs[3] + 8) // 8)
            iit_offset = at(regs[4], regs[5] * 4)
            table = at(regs[2], regs[3] * 8)
            entries = []
            for index in range(regs[3]):
                slot = table + index * 8
                if slot - base not in locations:
                    raise ValueError("Name pointer is not a registered chained fixup")
                word = struct.unpack_from("<Q", data, slot)[0]
                target, _ = decode_rebase(word)
                offset = at(target)
                section = next((s for s in sections if s["offset"] <= offset < s["offset"] + s["size"]), None)
                if not section:
                    raise ValueError("Intrinsic name is not in a C-string section")
                end = data.find(b"\0", offset, section["offset"] + section["size"])
                if end < 0:
                    raise ValueError("Unterminated table string")
                name = data[offset:end].decode("ascii")
                if not re.fullmatch(r"air\.[A-Za-z0-9_.]+", name):
                    raise ValueError("Unexpected intrinsic table name")
                identifier = index + 1
                overloaded = bool(data[overload_offset + identifier // 8] & (1 << (identifier % 8)))
                iit_raw = struct.unpack_from("<I", data, iit_offset + index * 4)[0]
                entries.append({"id": identifier, "name": name, "overloaded": overloaded, "iit_raw": iit_raw, "pointer_file_offset": slot, "string_file_offset": offset, "registered_rebase": True})
            names = [e["name"] for e in entries]
            if len(set(names)) != len(names) or names != sorted(names):
                raise ValueError("Expected sorted unique intrinsic name table")
            version = tag.replace("d", ".")
            result["versions"][version] = {"constructor": symbol, "command": command, "names_va": regs[2], "count": regs[3], "overload_bitset_va": overload_va, "iit_va": regs[4], "iit_count": regs[5], "long_iit_va": regs[6], "long_iit_size": regs[7], "entries": entries}
            print(version, len(entries), flush=True)
        (args.output / "tables.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
