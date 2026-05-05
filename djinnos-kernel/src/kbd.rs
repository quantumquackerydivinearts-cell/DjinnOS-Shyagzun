// Kernel keyboard ring buffer.
//
// Fed by the main event loop (keyboard poll); drained by sys_read (user-mode
// syscall).  Single-core, no locking needed.
//
// push() returns true if a blocked process was unblocked — the caller should
// NOT also forward the key to the shell in that case (user process owns input).

const BUF: usize = 64;

static mut KBD_DATA: [u8; BUF] = [0; BUF];
static mut KBD_HEAD: usize = 0;   // next read
static mut KBD_TAIL: usize = 0;   // next write

/// Push one byte.  Returns true if a stdin waiter was unblocked (key consumed).
pub fn push(byte: u8) -> bool {
    unsafe {
        let next = (KBD_TAIL + 1) % BUF;
        if next != KBD_HEAD {   // drop silently if full
            KBD_DATA[KBD_TAIL] = byte;
            KBD_TAIL = next;
        }
    }
    crate::process::unblock_stdin_waiters()
}

/// Pop one byte, or None if empty.
pub fn pop() -> Option<u8> {
    unsafe {
        if KBD_HEAD == KBD_TAIL { return None; }
        let b = KBD_DATA[KBD_HEAD];
        KBD_HEAD = (KBD_HEAD + 1) % BUF;
        Some(b)
    }
}

/// True if at least one byte is waiting.
pub fn available() -> bool {
    unsafe { KBD_HEAD != KBD_TAIL }
}

// ── User process stdout → GPU shell pipe ─────────────────────────────────────
// sys_write(fd=1/2) pushes bytes here; the kernel main loop drains and
// forwards them to the Ko shell display so user process output is visible
// on the GPU screen as well as the serial terminal.

const STDOUT_BUF: usize = 2048;
static mut STDOUT_DATA: [u8; STDOUT_BUF] = [0; STDOUT_BUF];
static mut STDOUT_HEAD: usize = 0;
static mut STDOUT_TAIL: usize = 0;

pub fn stdout_push(byte: u8) {
    unsafe {
        let next = (STDOUT_TAIL + 1) % STDOUT_BUF;
        if next != STDOUT_HEAD {
            STDOUT_DATA[STDOUT_TAIL] = byte;
            STDOUT_TAIL = next;
        }
    }
}

pub fn stdout_pop() -> Option<u8> {
    unsafe {
        if STDOUT_HEAD == STDOUT_TAIL { return None; }
        let b = STDOUT_DATA[STDOUT_HEAD];
        STDOUT_HEAD = (STDOUT_HEAD + 1) % STDOUT_BUF;
        Some(b)
    }
}