// installer.rs — DjinnOS native install to internal NVMe.
//
// Shell command: install
//
// Flow:
//   1. Initialise NVMe controller.
//   2. Read GPT — find EFI System Partition.
//   3. Locate loader.efi and krnl.elf in the ramdisk (loaded from USB).
//   4. Format the ESP as FAT32 and write the two files.
//   5. Report done. Pull USB and reboot.
//
// The ramdisk is populated by djinnos-loader from files in the root of the
// USB FAT32 partition.  flash_d.ps1 places loader.efi and krnl.elf there.

use crate::uart;

unsafe fn dump_byte(b: u8) {
    let d = b"0123456789abcdef";
    let buf = [d[((b >> 4) & 0xF) as usize], d[(b & 0xF) as usize]];
    uart::puts(core::str::from_utf8(&buf).unwrap_or("??"));
}

#[cfg(target_arch = "x86_64")]
pub fn run() -> &'static str {
    unsafe { run_inner() }
}
#[cfg(not(target_arch = "x86_64"))]
pub fn run() -> &'static str { "NOT SUPPORTED ON THIS ARCHITECTURE" }

#[cfg(target_arch = "x86_64")]
unsafe fn run_inner() -> &'static str {
    uart::puts("\r\n=== DjinnOS Installer ===\r\n");

    // ── Step 1: NVMe ─────────────────────────────────────────────────────────
    uart::puts("Step 1: Initialising NVMe...\r\n");
    if !crate::nvme::init() {
        return "FAIL: NVMe init failed. Is this machine's SSD NVMe?";
    }
    uart::puts("       NVMe ready. LBA size=");
    uart::putu(crate::nvme::lba_size() as u64);
    uart::puts(" total=");
    uart::putu(crate::nvme::lba_count());
    uart::puts("\r\n");

    // ── Step 2: GPT ──────────────────────────────────────────────────────────
    uart::puts("Step 2: Reading GPT...\r\n");

    // Diagnostic: dump first 8 bytes of LBA 1 (should be "EFI PART" = 45 46 49 20 50 41 52 54).
    if crate::nvme::read_lba(1) {
        uart::puts("       LBA1[0..8]:");
        for i in 0..8usize {
            uart::puts(" ");
            unsafe { dump_byte(crate::nvme::XFER.data[i]); }
        }
        uart::puts("\r\n");
        uart::puts("       (expect: 45 46 49 20 50 41 52 54 = EFI PART)\r\n");
    } else {
        return "FAIL: NVMe read of LBA 1 failed.";
    }

    let esp = match crate::gpt::find_esp() {
        Some(p) => p,
        None    => return "FAIL: no EFI System Partition found in GPT.",
    };
    let esp_sectors = esp.end_lba - esp.start_lba + 1;
    uart::puts("       ESP: start=");
    uart::putu(esp.start_lba);
    uart::puts(" sectors=");
    uart::putu(esp_sectors);
    uart::puts("\r\n");

    if esp_sectors < 204800 {
        // Warn if ESP is under 100 MiB — might be too small.
        uart::puts("       Warning: ESP is under 100 MiB.\r\n");
    }

    // ── Step 3: Ramdisk files ────────────────────────────────────────────────
    uart::puts("Step 3: Locating boot files in ramdisk...\r\n");

    let loader = crate::ramdisk::find(b"loader.efi");
    let kernel  = crate::ramdisk::find(b"krnl.elf");

    if loader.is_none() {
        return "FAIL: loader.efi not in ramdisk. \
                Re-flash USB with flash_d.ps1 (it copies loader.efi to USB root).";
    }
    if kernel.is_none() {
        return "FAIL: kernel.elf not in ramdisk. \
                Re-flash USB with flash_d.ps1.";
    }

    let loader_data = loader.unwrap();
    let kernel_data = kernel.unwrap();
    let firmware_data = crate::ramdisk::find(b"rtw8852a.bin");

    uart::puts("       loader.efi: ");
    uart::putu(loader_data.len() as u64);
    uart::puts(" bytes\r\n");
    uart::puts("       krnl.elf:   ");
    uart::putu(kernel_data.len() as u64);
    uart::puts(" bytes\r\n");
    if let Some(fw) = firmware_data {
        uart::puts("       rtw8852a.bin: ");
        uart::putu(fw.len() as u64);
        uart::puts(" bytes\r\n");
    } else {
        uart::puts("       rtw8852a.bin: not present (WiFi firmware not installed)\r\n");
    }

    // ── Step 4: Format ESP and write files ───────────────────────────────────
    uart::puts("Step 4: Formatting ESP and writing files...\r\n");
    uart::puts("        (This erases the Windows boot partition. No going back.)\r\n");

    let ok = crate::fat32w::format_and_write(
        esp.start_lba,
        esp.end_lba,
        loader_data,
        kernel_data,
        firmware_data,
    );

    if !ok {
        return "FAIL: FAT32 write failed. Check UART log for details.";
    }

    // ── Done ─────────────────────────────────────────────────────────────────
    uart::puts("\r\n=== Install complete ===\r\n");
    uart::puts("Pull the USB drive and reboot. DjinnOS will boot from the SSD.\r\n");

    "Install complete. Pull USB and reboot."
}
