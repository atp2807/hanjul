"""Pure-stdlib OLE2 Compound Document reader.

Parses the binary container format used by HWP 5.x, DOC, XLS, PPT, etc.
Only stdlib (struct) is required — no olefile dependency.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
ENDOFCHAIN = 0xFFFFFFFE
FREESECT = 0xFFFFFFFF
MAXREGSECT = 0xFFFFFFFA
NOSTREAM = 0xFFFFFFFF

# Directory entry object types
_STORAGE = 1
_STREAM = 2
_ROOT = 5


@dataclass
class OLE2Document:
    """Parsed OLE2 container — maps stream path to raw bytes."""

    streams: dict[str, bytes] = field(default_factory=dict)


def read_ole2(data: bytes) -> OLE2Document:
    """Parse *data* as an OLE2 compound document and return an `OLE2Document`."""
    if len(data) < 512 or data[:8] != OLE2_SIGNATURE:
        raise ValueError("Not a valid OLE2 file (bad signature)")

    # --- Header -----------------------------------------------------------
    sector_shift = struct.unpack_from("<H", data, 30)[0]
    sector_size = 1 << sector_shift
    mini_sector_shift = struct.unpack_from("<H", data, 32)[0]
    mini_sector_size = 1 << mini_sector_shift
    first_dir_sector = struct.unpack_from("<I", data, 48)[0]
    mini_stream_cutoff = struct.unpack_from("<I", data, 56)[0]
    first_mini_fat_sector = struct.unpack_from("<I", data, 60)[0]
    mini_fat_sector_count = struct.unpack_from("<I", data, 64)[0]
    first_difat_sector = struct.unpack_from("<I", data, 68)[0]
    difat_sector_count = struct.unpack_from("<I", data, 72)[0]

    header_size = 512  # always 512 regardless of sector_size

    def _sector_offset(sec_id: int) -> int:
        return header_size + sec_id * sector_size

    # --- DIFAT → FAT sector list ------------------------------------------
    difat: list[int] = []
    for i in range(109):
        val = struct.unpack_from("<I", data, 76 + i * 4)[0]
        if val <= MAXREGSECT:
            difat.append(val)

    # Follow DIFAT chain for >109 FAT sectors
    cur = first_difat_sector
    for _ in range(difat_sector_count):
        if cur > MAXREGSECT:
            break
        off = _sector_offset(cur)
        entries_per = sector_size // 4 - 1  # last dword = next DIFAT sector
        for j in range(entries_per):
            val = struct.unpack_from("<I", data, off + j * 4)[0]
            if val <= MAXREGSECT:
                difat.append(val)
        cur = struct.unpack_from("<I", data, off + entries_per * 4)[0]

    # --- Build FAT ---------------------------------------------------------
    fat: list[int] = []
    for sec_id in difat:
        off = _sector_offset(sec_id)
        for j in range(sector_size // 4):
            fat.append(struct.unpack_from("<I", data, off + j * 4)[0])

    def _read_chain(start: int) -> list[int]:
        chain: list[int] = []
        cur = start
        while cur <= MAXREGSECT and cur < len(fat):
            chain.append(cur)
            cur = fat[cur]
            if len(chain) > 10_000:
                raise ValueError("FAT chain too long — possible corruption")
        return chain

    def _read_stream_data(start: int, size: int) -> bytes:
        chain = _read_chain(start)
        buf = bytearray()
        for sec_id in chain:
            off = _sector_offset(sec_id)
            buf.extend(data[off : off + sector_size])
        return bytes(buf[:size])

    # --- Directory entries -------------------------------------------------
    dir_data = _read_stream_data(first_dir_sector, len(data))  # read full chain

    @dataclass
    class _DirEntry:
        name: str
        obj_type: int
        start_sector: int
        size: int
        child_id: int
        left_id: int
        right_id: int

    entries: list[_DirEntry] = []
    for i in range(len(dir_data) // 128):
        raw = dir_data[i * 128 : (i + 1) * 128]
        name_len = struct.unpack_from("<H", raw, 64)[0]
        name = raw[:name_len].decode("utf-16-le", errors="replace").rstrip("\x00")
        obj_type = raw[66]
        left_id = struct.unpack_from("<I", raw, 68)[0]
        right_id = struct.unpack_from("<I", raw, 72)[0]
        child_id = struct.unpack_from("<I", raw, 76)[0]
        start_sector = struct.unpack_from("<I", raw, 116)[0]
        size = struct.unpack_from("<I", raw, 120)[0]
        if obj_type > 0:
            entries.append(
                _DirEntry(name, obj_type, start_sector, size, child_id, left_id, right_id)
            )

    if not entries or entries[0].obj_type != _ROOT:
        raise ValueError("Missing Root Entry in OLE2 directory")

    root_entry = entries[0]

    # --- Mini stream (for streams < mini_stream_cutoff) --------------------
    root_stream = _read_stream_data(root_entry.start_sector, root_entry.size)

    mini_fat: list[int] = []
    if mini_fat_sector_count > 0 and first_mini_fat_sector <= MAXREGSECT:
        for sec_id in _read_chain(first_mini_fat_sector):
            off = _sector_offset(sec_id)
            for j in range(sector_size // 4):
                mini_fat.append(struct.unpack_from("<I", data, off + j * 4)[0])

    def _read_mini_stream(start: int, size: int) -> bytes:
        chain: list[int] = []
        cur = start
        while cur <= MAXREGSECT and cur < len(mini_fat):
            chain.append(cur)
            cur = mini_fat[cur]
            if len(chain) > 10_000:
                raise ValueError("Mini FAT chain too long")
        buf = bytearray()
        for ms_id in chain:
            off = ms_id * mini_sector_size
            buf.extend(root_stream[off : off + mini_sector_size])
        return bytes(buf[:size])

    # --- Build path → bytes mapping via red-black tree traversal -----------
    doc = OLE2Document()

    def _walk(entry_idx: int, path_prefix: str) -> None:
        """Walk the directory red-black tree and populate doc.streams."""
        if entry_idx >= len(entries) or entry_idx == NOSTREAM:
            return

        e = entries[entry_idx]

        if e.left_id != NOSTREAM and e.left_id < len(entries):
            _walk(e.left_id, path_prefix)
        if e.right_id != NOSTREAM and e.right_id < len(entries):
            _walk(e.right_id, path_prefix)

        if e.obj_type == _STREAM:
            full_path = f"{path_prefix}{e.name}" if path_prefix else e.name
            if e.size < mini_stream_cutoff:
                doc.streams[full_path] = _read_mini_stream(e.start_sector, e.size)
            else:
                doc.streams[full_path] = _read_stream_data(e.start_sector, e.size)

        if e.obj_type == _STORAGE:
            new_prefix = f"{path_prefix}{e.name}/"
            if e.child_id != NOSTREAM and e.child_id < len(entries):
                _walk(e.child_id, new_prefix)

    # Start from Root Entry's child
    if root_entry.child_id != NOSTREAM and root_entry.child_id < len(entries):
        _walk(root_entry.child_id, "")

    return doc
