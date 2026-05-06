// CMOS Real-Time Clock driver.
//
// I/O ports:
//   0x70  CMOS index register (write register number here)
//   0x71  CMOS data register  (read or write the selected register)
//
// Standard register map:
//   0x00  seconds     0x02  minutes     0x04  hours
//   0x06  weekday     0x07  day         0x08  month    0x09  year
//   0x0A  status A    0x0B  status B    0x32  century
//
// Status A bit 7: update-in-progress — read twice and compare to avoid
// torn reads.  Status B bit 2: binary mode (else BCD).  Bit 1: 24-hour mode.

use crate::arch::{inb, outb};

const CMOS_IDX: u16 = 0x70;
const CMOS_DAT: u16 = 0x71;

fn read_reg(r: u8) -> u8 {
    unsafe {
        outb(CMOS_IDX, r);
        inb(CMOS_DAT)
    }
}

fn updating() -> bool { read_reg(0x0A) & 0x80 != 0 }

fn from_bcd(v: u8) -> u8 { (v >> 4) * 10 + (v & 0x0F) }

pub struct DateTime {
    pub year:   u16,
    pub month:  u8,
    pub day:    u8,
    pub hour:   u8,
    pub minute: u8,
    pub second: u8,
}

/// Read the current date and time from the CMOS RTC.
/// Safe to call from any context; spins briefly waiting for the UIP bit.
pub fn read() -> DateTime {
    // Wait for any in-progress update to finish (takes < 2 ms).
    while updating() {}

    let sec  = read_reg(0x00);
    let min  = read_reg(0x02);
    let hr   = read_reg(0x04);
    let day  = read_reg(0x07);
    let mon  = read_reg(0x08);
    let yr   = read_reg(0x09);
    let cent = read_reg(0x32);
    let b    = read_reg(0x0B);

    let binary  = b & 0x04 != 0;
    let mode_24 = b & 0x02 != 0;

    let (s, mn, h, d, mo, y, c) = if binary {
        (sec, min, hr & 0x7F, day, mon, yr, cent)
    } else {
        (from_bcd(sec), from_bcd(min), from_bcd(hr & 0x7F),
         from_bcd(day), from_bcd(mon), from_bcd(yr), from_bcd(cent))
    };

    // 12-hour → 24-hour conversion: if PM bit is set and hour ≠ 12, add 12.
    let h = if !mode_24 && (hr & 0x80 != 0) {
        if h == 12 { 12 } else { h + 12 }
    } else {
        h
    };

    // Century: use CMOS 0x32 if valid, otherwise assume 21st century.
    let full_year: u16 = if c >= 19 && c <= 22 {
        (c as u16) * 100 + y as u16
    } else {
        2000 + y as u16
    };

    DateTime { year: full_year, month: mo, day: d, hour: h, minute: mn, second: s }
}

/// Write a two-digit decimal number into buf at offset, return new offset.
fn put2(buf: &mut [u8], off: usize, v: u8) -> usize {
    buf[off]     = b'0' + v / 10;
    buf[off + 1] = b'0' + v % 10;
    off + 2
}

/// Format as "YYYY-MM-DD  HH:MM:SS" into a fixed 80-byte buffer.
pub fn format(dt: &DateTime, buf: &mut [u8; 80]) -> usize {
    let yr = dt.year;
    buf[0] = b'0' + ((yr / 1000) % 10) as u8;
    buf[1] = b'0' + ((yr /  100) % 10) as u8;
    buf[2] = b'0' + ((yr /   10) % 10) as u8;
    buf[3] = b'0' + ( yr         % 10) as u8;
    buf[4] = b'-';
    let mut i = put2(buf, 5, dt.month);
    buf[i] = b'-'; i += 1;
    i = put2(buf, i, dt.day);
    buf[i] = b' '; buf[i+1] = b' '; i += 2;
    i = put2(buf, i, dt.hour);
    buf[i] = b':'; i += 1;
    i = put2(buf, i, dt.minute);
    buf[i] = b':'; i += 1;
    i = put2(buf, i, dt.second);
    i
}
