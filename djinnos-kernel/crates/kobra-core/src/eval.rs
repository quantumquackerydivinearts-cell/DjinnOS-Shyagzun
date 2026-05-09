// Evaluator — pretty-print the AST with tongue coverage.
//
// All output goes through the Output trait so this module is usable in both
// the bare-metal kobra-vm tool (SBI syscall output) and the DjinnOS kernel
// (UART / shell line buffer output).

use crate::ast::{Pool, Node, collect_addresses};
use crate::tongue::{classify, Space};

// ── Output trait ──────────────────────────────────────────────────────────────

pub trait Output {
    fn write(&mut self, s: &[u8]);
}

// ── Public entry point ────────────────────────────────────────────────────────

pub fn eval<O: Output>(pool: &Pool, root: u8, out: &mut O) {
    print_node(pool, root, 0, out);
    out.write(b"\r\n");

    // Tongue coverage report
    let mut addrs = [0u16; 64];
    let mut count = 0;
    collect_addresses(pool, root, &mut addrs, &mut count);

    if count == 0 { return; }

    // Count per tongue (only actual Tongue entries, not Reserved)
    let mut tongue_counts = [(0u8, "" as &str, 0u8); 37];
    let mut tongue_seen = 0usize;

    for i in 0..count {
        let addr = addrs[i];
        if addr == u16::MAX { continue; }
        if let Space::Tongue(num, name) = classify(addr) {
            let mut found = false;
            for j in 0..tongue_seen {
                if tongue_counts[j].0 == num {
                    tongue_counts[j].2 += 1;
                    found = true;
                    break;
                }
            }
            if !found && tongue_seen < 37 {
                tongue_counts[tongue_seen] = (num, name, 1);
                tongue_seen += 1;
            }
        }
    }

    // Sort by tongue number
    for i in 0..tongue_seen {
        for j in i+1..tongue_seen {
            if tongue_counts[j].0 < tongue_counts[i].0 {
                tongue_counts.swap(i, j);
            }
        }
    }

    out.write(b"  tongues:");
    for i in 0..tongue_seen {
        let (_, name, n) = tongue_counts[i];
        out.write(b" ");
        out.write(name.as_bytes());
        if n > 1 {
            out.write(b"\xd7");
            write_u8(n, out);
        }
    }
    out.write(b"\r\n");
}

// ── Internal helpers ──────────────────────────────────────────────────────────

fn print_node<O: Output>(pool: &Pool, idx: u8, depth: u8, out: &mut O) {
    match pool.get(idx) {
        Node::Symbol { name, .. } => {
            out.write(name.as_bytes());
        }
        Node::Unknown { .. } => {
            out.write(b"?(?)");
        }
        Node::Wunashako { ch, n } => {
            out.write(b"[ ");
            for i in 0..n {
                if i > 0 { out.write(b" "); }
                let child = pool.children[(ch + i) as usize];
                print_node(pool, child, depth, out);
            }
            out.write(b" ]");
        }
        Node::Group { ch, n } => {
            out.write(b"{\r\n");
            for i in 0..n {
                print_indent(depth + 1, out);
                let child = pool.children[(ch + i) as usize];
                print_node(pool, child, depth + 1, out);
                out.write(b"\r\n");
            }
            print_indent(depth, out);
            out.write(b"}");
        }
        Node::Apply { func, arg } => {
            print_node(pool, func, depth, out);
            out.write(b"(");
            print_node(pool, arg, depth, out);
            out.write(b")");
        }
        Node::Sub { lhs, rhs } => {
            print_node(pool, lhs, depth, out);
            out.write(b" : ");
            print_node(pool, rhs, depth, out);
        }
        Node::Seq { ch, n } => {
            for i in 0..n {
                if i > 0 { out.write(b" ; "); }
                let child = pool.children[(ch + i) as usize];
                print_node(pool, child, depth, out);
            }
        }
    }
}

fn print_indent<O: Output>(depth: u8, out: &mut O) {
    for _ in 0..depth { out.write(b"  "); }
}

fn write_u8<O: Output>(n: u8, out: &mut O) {
    let mut buf = [b'0'; 3];
    let mut i = 3usize;
    let mut v = n;
    if v == 0 { out.write(b"0"); return; }
    while v > 0 { i -= 1; buf[i] = b'0' + (v % 10); v /= 10; }
    out.write(&buf[i..]);
}