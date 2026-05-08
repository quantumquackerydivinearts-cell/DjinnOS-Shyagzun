#!/usr/bin/env python3
"""
make_img.py  --  DjinnOS bootable UEFI disk image builder.
Pure Python stdlib, no external tools required.

Produces a 64 MiB raw disk image:
  LBA 0       Protective MBR
  LBA 1       Primary GPT header
  LBA 2-33    GPT partition entries
  LBA 2048    EFI System Partition (FAT32, ~62 MiB)
               EFI/BOOT/BOOTX64.EFI   <- the UEFI loader
               KERNEL.ELF             <- the kernel (8.3 name for kernel.elf)
  LBA 131040  Backup GPT entries
  LBA 131071  Backup GPT header

Usage:  python make_img.py <loader.efi> <kernel-elf> <output.img>
"""

import struct, zlib, uuid, sys
from pathlib import Path

# ---- geometry ----------------------------------------------------------------

SECTOR      = 512
IMG_SECTS   = 131072          # 64 MiB
PART_START  = 2048            # first LBA of EFI partition
PART_END    = 131038          # last LBA of EFI partition (inclusive)
PART_SECTS  = PART_END - PART_START + 1  # 128991 sectors

# FAT32 parameters
SPC         = 8               # sectors per cluster (4 KiB)
RESERVED    = 32              # reserved sectors (BPB + FSInfo + backup + padding)
NUM_FATS    = 2
FAT_SECTS   = 128             # sectors per FAT
DATA_START  = RESERVED + NUM_FATS * FAT_SECTS  # 288

ROOT_CLUST  = 2               # FAT32 root directory starts at cluster 2

# ---- helpers -----------------------------------------------------------------

def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF

# ---- Protective MBR ---------------------------------------------------------

def make_pmbr() -> bytes:
    mbr = bytearray(512)
    off = 446
    mbr[off + 4] = 0xEE                         # type: GPT protective
    mbr[off + 5] = mbr[off + 6] = mbr[off + 7] = 0xFF   # CHS end
    struct.pack_into('<I', mbr, off + 8,  1)
    struct.pack_into('<I', mbr, off + 12, min(IMG_SECTS - 1, 0xFFFF_FFFF))
    mbr[510] = 0x55
    mbr[511] = 0xAA
    return bytes(mbr)

# ---- GPT --------------------------------------------------------------------

EFI_PART_GUID = uuid.UUID('{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}').bytes_le

def make_gpt_header(my_lba, alt_lba, entries_lba, entries_crc,
                    first_usable, last_usable, disk_guid) -> bytes:
    h = bytearray(92)
    h[0:8] = b'EFI PART'
    struct.pack_into('<I', h,  8, 0x0001_0000)   # revision 1.0
    struct.pack_into('<I', h, 12, 92)             # header size
    # offset 16: CRC32 (zeroed then computed)
    struct.pack_into('<Q', h, 24, my_lba)
    struct.pack_into('<Q', h, 32, alt_lba)
    struct.pack_into('<Q', h, 40, first_usable)
    struct.pack_into('<Q', h, 48, last_usable)
    h[56:72] = disk_guid
    struct.pack_into('<Q', h, 72, entries_lba)
    struct.pack_into('<I', h, 80, 128)            # max entries
    struct.pack_into('<I', h, 84, 128)            # entry size
    struct.pack_into('<I', h, 88, entries_crc)
    struct.pack_into('<I', h, 16, crc32(bytes(h)))
    return bytes(h)

def make_gpt_entries(disk_part_guid: bytes) -> bytes:
    e = bytearray(128)
    e[0:16]  = EFI_PART_GUID        # partition type GUID
    e[16:32] = disk_part_guid       # unique partition GUID
    struct.pack_into('<Q', e, 32, PART_START)
    struct.pack_into('<Q', e, 40, PART_END)
    struct.pack_into('<Q', e, 48, 0)             # attributes
    e[56:70] = "DjinnOS".encode('utf-16-le')     # partition name
    # Pad to 32 * SECTOR bytes
    return bytes(e).ljust(32 * SECTOR, b'\x00')

# ---- FAT32 BPB + FSInfo -----------------------------------------------------

def make_bpb() -> bytes:
    b = bytearray(512)
    b[0:3]  = b'\xEB\x58\x90'
    b[3:11] = b'MSDOS5.0'
    struct.pack_into('<H', b, 11, SECTOR)
    b[13]   = SPC
    struct.pack_into('<H', b, 14, RESERVED)
    b[16]   = NUM_FATS
    struct.pack_into('<H', b, 17, 0)             # root entry count (FAT32 = 0)
    struct.pack_into('<H', b, 19, 0)             # total sectors 16 (use 32-bit)
    b[21]   = 0xF8                               # media descriptor
    struct.pack_into('<H', b, 22, 0)             # sectors per FAT 16 (use 32-bit)
    struct.pack_into('<H', b, 24, 63)
    struct.pack_into('<H', b, 26, 255)
    struct.pack_into('<I', b, 28, PART_START)    # hidden sectors
    struct.pack_into('<I', b, 32, PART_SECTS)
    struct.pack_into('<I', b, 36, FAT_SECTS)
    struct.pack_into('<H', b, 40, 0)             # ext flags
    struct.pack_into('<H', b, 42, 0)             # FS version 0.0
    struct.pack_into('<I', b, 44, ROOT_CLUST)
    struct.pack_into('<H', b, 48, 1)             # FSInfo sector
    struct.pack_into('<H', b, 50, 6)             # backup boot sector
    b[64]   = 0x80                               # drive number
    b[66]   = 0x29                               # ext boot sig
    struct.pack_into('<I', b, 67, 0xDEAD_BABE)
    b[71:82] = b'DJINNOS    '
    b[82:90] = b'FAT32   '
    b[510] = 0x55; b[511] = 0xAA
    return bytes(b)

def make_fsinfo() -> bytes:
    fs = bytearray(512)
    struct.pack_into('<I', fs,   0, 0x4161_5252)
    struct.pack_into('<I', fs, 484, 0x6141_7272)
    struct.pack_into('<I', fs, 488, 0xFFFF_FFFF)
    struct.pack_into('<I', fs, 492, 0xFFFF_FFFF)
    struct.pack_into('<I', fs, 508, 0xAA55_0000)
    fs[510] = 0x55; fs[511] = 0xAA
    return bytes(fs)

# ---- FAT32 filesystem builder -----------------------------------------------

class Fat32Builder:
    """Builds a FAT32 volume in memory (PART_SECTS x SECTOR bytes)."""

    def __init__(self):
        self._img   = bytearray(PART_SECTS * SECTOR)
        # FAT array: indices 0..max_cluster, values = next cluster (or EOC/FREE)
        max_entries = FAT_SECTS * SECTOR // 4
        self._fat   = [0] * max_entries
        self._fat[0] = 0x0FFF_FFF8   # media descriptor cluster
        self._fat[1] = 0x0FFF_FFFF   # reserved
        self._next   = ROOT_CLUST    # next free cluster to allocate
        # Root directory: occupy cluster 2, no children yet
        self._root_dir: list = []
        self._alloc_cluster()        # allocate cluster 2 for root

    # -- cluster management ---------------------------------------------------

    def _alloc_cluster(self) -> int:
        c = self._next
        self._next += 1
        self._fat[c] = 0x0FFF_FFFF   # mark as EOC
        return c

    def _alloc_chain(self, n: int) -> list:
        """Allocate a chain of n clusters, link them in the FAT."""
        chain = [self._alloc_cluster() for _ in range(n)]
        for i in range(len(chain) - 1):
            self._fat[chain[i]] = chain[i + 1]
        return chain

    def _cluster_off(self, c: int) -> int:
        return (DATA_START + (c - ROOT_CLUST) * SPC) * SECTOR

    def _write_to_cluster(self, c: int, data: bytes):
        off = self._cluster_off(c)
        n   = min(len(data), SPC * SECTOR)
        self._img[off : off + n] = data[:n]

    # -- directory + file creation --------------------------------------------

    def _make_dir_entry(self, name8: str, ext3: str, attr: int,
                        first_clust: int, size: int) -> bytes:
        d = bytearray(32)
        d[0:8]  = name8.upper().ljust(8)[:8].encode('ascii', errors='replace')
        d[8:11] = ext3.upper().ljust(3)[:3].encode('ascii', errors='replace')
        d[11]   = attr
        struct.pack_into('<H', d, 20, (first_clust >> 16) & 0xFFFF)
        struct.pack_into('<H', d, 26,  first_clust        & 0xFFFF)
        struct.pack_into('<I', d, 28, size)
        return bytes(d)

    def mkdir(self, path_parts: list) -> list:
        """Ensure path_parts directories exist; return the innermost dir list."""
        current = self._root_dir
        for name in path_parts:
            name_up = name.upper()[:8]
            found   = next((e for e in current
                            if e['attr'] & 0x10 and e['name'] == name_up), None)
            if found is None:
                c    = self._alloc_cluster()
                found = {'name': name_up, 'ext': '   ', 'attr': 0x10,
                         'clust': c, 'size': 0, 'children': []}
                current.append(found)
            current = found['children']
        return current

    def add_file(self, path: str, data: bytes):
        """
        path: forward-slash or backslash path, e.g. 'EFI/BOOT/BOOTX64.EFI'
        The filename MUST be 8.3 compatible (no LFN).
        """
        parts    = [p for p in path.replace('\\', '/').split('/') if p]
        filename = parts[-1].upper()
        dot      = filename.rfind('.')
        name8    = filename[:dot].ljust(8)[:8] if dot >= 0 else filename.ljust(8)[:8]
        ext3     = filename[dot+1:].ljust(3)[:3] if dot >= 0 else '   '
        parent   = self.mkdir(parts[:-1])

        clust_size = SPC * SECTOR
        n_clust    = max(1, (len(data) + clust_size - 1) // clust_size)
        chain      = self._alloc_chain(n_clust)

        for i, c in enumerate(chain):
            chunk = data[i * clust_size : (i + 1) * clust_size]
            self._write_to_cluster(c, chunk)

        parent.append({'name': name8, 'ext': ext3, 'attr': 0x20,
                       'clust': chain[0], 'size': len(data), 'children': []})

    # -- serialise ------------------------------------------------------------

    def _write_dir_entries(self, entries: list, clust: int):
        """Write directory entries into `clust`, recurse into subdirs."""
        raw = bytearray()
        for e in entries:
            raw += self._make_dir_entry(e['name'], e['ext'], e['attr'],
                                        e['clust'], e['size'])
        raw += b'\x00' * 32   # null terminator
        self._write_to_cluster(clust, bytes(raw))
        for e in entries:
            if e['attr'] & 0x10:
                self._write_dir_entries(e['children'], e['clust'])

    def build(self) -> bytes:
        # BPB and FSInfo
        self._img[0 * SECTOR : 1 * SECTOR] = make_bpb()
        self._img[1 * SECTOR : 2 * SECTOR] = make_fsinfo()

        # Write FATs
        fat_bytes = struct.pack('<' + 'I' * len(self._fat), *self._fat)
        fat_off   = RESERVED * SECTOR
        for f in range(NUM_FATS):
            start = fat_off + f * FAT_SECTS * SECTOR
            self._img[start : start + FAT_SECTS * SECTOR] = \
                fat_bytes[:FAT_SECTS * SECTOR]

        # Write directory tree
        self._write_dir_entries(self._root_dir, ROOT_CLUST)

        return bytes(self._img)


# ---- main -------------------------------------------------------------------

def build(loader_path: str, kernel_path: str, out_path: str):
    print(f"Reading loader:  {loader_path}")
    loader = Path(loader_path).read_bytes()
    print(f"  {len(loader):,} bytes")

    print(f"Reading kernel:  {kernel_path}")
    kernel = Path(kernel_path).read_bytes()
    print(f"  {len(kernel):,} bytes")

    print(f"Building FAT32 partition ({PART_SECTS} sectors = {PART_SECTS*SECTOR//1024//1024} MiB)...")
    fat = Fat32Builder()
    fat.add_file('EFI/BOOT/BOOTX64.EFI', loader)
    fat.add_file('kernel.elf', kernel)          # 8.3: KERNEL.ELF
    part_img = fat.build()

    print(f"Building GPT disk image (64 MiB)...")
    disk       = bytearray(IMG_SECTS * SECTOR)
    disk_guid  = uuid.uuid4().bytes_le
    part_guid  = uuid.uuid4().bytes_le
    entries    = make_gpt_entries(part_guid)
    e_crc      = crc32(entries)
    BACKUP_ENT = IMG_SECTS - 1 - 32

    disk[0 : SECTOR]            = make_pmbr()
    disk[SECTOR : SECTOR + 92]  = make_gpt_header(1, IMG_SECTS-1, 2, e_crc,
                                                   PART_START, PART_END, disk_guid)
    disk[2*SECTOR : 2*SECTOR + len(entries)] = entries
    disk[PART_START*SECTOR : PART_START*SECTOR + len(part_img)] = part_img
    disk[BACKUP_ENT*SECTOR : BACKUP_ENT*SECTOR + len(entries)]  = entries
    disk[(IMG_SECTS-1)*SECTOR : (IMG_SECTS-1)*SECTOR + 92] = \
        make_gpt_header(IMG_SECTS-1, 1, BACKUP_ENT, e_crc,
                        PART_START, PART_END, disk_guid)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(disk)
    mib = len(disk) / 1024 / 1024
    print(f"Image written:   {out_path}  ({mib:.0f} MiB)")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python make_img.py <loader.efi> <kernel-elf> <output.img>')
        sys.exit(1)
    build(sys.argv[1], sys.argv[2], sys.argv[3])