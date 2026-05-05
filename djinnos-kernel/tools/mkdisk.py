#!/usr/bin/env python3
"""
mkdisk.py — DjinnOS Grapevine disk image builder.

Grapevine tongue filesystem layout (from the byte table):
  Sector  0      : Sa  (156) root volume header
  Sectors 1–16   : Seth (159) directory — up to 128 Sao entries, 64 bytes each
  Sectors 17+    : Sao (157) file data, one file per run of sectors

Volume header (sector 0, 512 bytes):
  [0:8]   magic   = b"DJINNOS\x00"
  [8:40]  name    = volume name (null-padded)
  [40:44] count   = u32 LE — number of files
  [44:]   reserved

Sao entry (64 bytes):
  [0:32]  name    = filename (null-padded)
  [32:36] start   = u32 LE — first data sector
  [36:40] length  = u32 LE — file length in bytes
  [40:64] reserved
"""

import struct, os, sys

SECTOR       = 512
MAGIC        = b"DJINNOS\x00"
ENTRY_SIZE   = 64
ENTRIES_PER_SECTOR = SECTOR // ENTRY_SIZE   # 8
TABLE_SECTORS      = 16                     # sectors 1-16
MAX_FILES          = TABLE_SECTORS * ENTRIES_PER_SECTOR  # 128
DATA_START         = 1 + TABLE_SECTORS       # sector 17


def pad(data, n):
    data = data[:n]
    return data + b"\x00" * (n - len(data))


def create_disk(output_path, source_dir, size_mb=32):
    total_sectors = size_mb * 1024 * 1024 // SECTOR
    disk = bytearray(total_sectors * SECTOR)

    files = []
    if os.path.isdir(source_dir):
        for fname in sorted(os.listdir(source_dir)):
            fpath = os.path.join(source_dir, fname)
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    files.append((fname.encode("utf-8")[:31], f.read()))

    if len(files) > MAX_FILES:
        print(f"Warning: truncating to {MAX_FILES} files")
        files = files[:MAX_FILES]

    # ── Sa volume header (sector 0) ────────────────────────────────────────
    header = (MAGIC
              + pad(b"DjinnOS root volume", 32)
              + struct.pack("<I", len(files))
              + b"\x00" * (SECTOR - 44))
    disk[0:SECTOR] = header[:SECTOR]

    # ── Seth directory + Sao file data ─────────────────────────────────────
    current_sector = DATA_START
    entries = []

    for name_bytes, data in files:
        start  = current_sector
        length = len(data)
        n_sec  = (length + SECTOR - 1) // SECTOR

        # write data sectors
        for i in range(n_sec):
            chunk = data[i * SECTOR:(i + 1) * SECTOR]
            chunk = pad(chunk, SECTOR)
            off   = (start + i) * SECTOR
            disk[off:off + SECTOR] = chunk

        entries.append((name_bytes, start, length))
        current_sector += max(1, n_sec)

    # write Sao entries into table sectors 1-16
    for i, (name, start, length) in enumerate(entries):
        entry = (pad(name + b"\x00", 32)
                 + struct.pack("<II", start, length)
                 + b"\x00" * 24)
        t_sec     = 1 + i // ENTRIES_PER_SECTOR
        t_off_sec = (i % ENTRIES_PER_SECTOR) * ENTRY_SIZE
        off       = t_sec * SECTOR + t_off_sec
        disk[off:off + ENTRY_SIZE] = entry

    with open(output_path, "wb") as f:
        f.write(disk)

    print(f"  disk: {output_path}  ({size_mb} MiB, {len(files)} files)")
    for name, start, length in entries:
        print(f"    {name.decode()} @ sector {start}  {length} B")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "disk.img"
    src = sys.argv[2] if len(sys.argv) > 2 else "tools/disk"
    create_disk(out, src)