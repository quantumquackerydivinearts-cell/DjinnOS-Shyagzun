// Phase 1 evaluator: pretty-print the AST with addresses and tongue coverage.

use crate::ast::{Pool, Node, collect_addresses};
use crate::tongue::{classify, Space};
use crate::syscall::{print, println};

pub fn eval(pool: &Pool, root: u8) {
    // Print the expression structure
    print_node(pool, root, 0);
    print(b"\r\n");

    // Tongue coverage report
    let mut addrs = [0u16; 64];
    let mut count = 0;
    collect_addresses(pool, root, &mut addrs, &mut count);

    if count > 0 {
        // Count per tongue (only actual Tongue entries, not Reserved)
        let mut tongue_counts = [(0u8, &"" as &str, 0u8); 37];
        let mut tongue_seen = 0usize;

        for i in 0..count {
            let addr = addrs[i];
            if addr == u16::MAX { continue; }
            if let Space::Tongue(num, name) = classify(addr) {
                // Find or insert
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

        print(b"  tongues:");
        for i in 0..tongue_seen {
            let (num, name, n) = tongue_counts[i];
            print(b" ");
            print(name.as_bytes());
            if n > 1 {
                print(b"\xd7");  // ×
                print_u8(n);
            }
        }
        println(b"");
    }
}

fn print_node(pool: &Pool, idx: u8, depth: u8) {
    match pool.get(idx) {
        Node::Symbol { addr, name } => {
            print(name.as_bytes());
            print(b"(");
            print_u16(addr);
            print(b")");
        }
        Node::Unknown { start, len } => {
            print(b"?");
            // Can't easily recover raw bytes here without the pool's word buffer
            print(b"(?)");
        }
        Node::Wunashako { ch, n } => {
            print(b"[ ");
            for i in 0..n {
                if i > 0 { print(b" "); }
                let child = pool.children[(ch + i) as usize];
                print_node(pool, child, depth);
            }
            print(b" ]");
        }
        Node::Group { ch, n } => {
            println(b"{");
            for i in 0..n {
                print_indent(depth + 1);
                let child = pool.children[(ch + i) as usize];
                print_node(pool, child, depth + 1);
                println(b"");
            }
            print_indent(depth);
            print(b"}");
        }
        Node::Apply { func, arg } => {
            print_node(pool, func, depth);
            print(b"(");
            print_node(pool, arg, depth);
            print(b")");
        }
        Node::Sub { lhs, rhs } => {
            print_node(pool, lhs, depth);
            print(b" : ");
            print_node(pool, rhs, depth);
        }
        Node::Seq { ch, n } => {
            for i in 0..n {
                if i > 0 { print(b" ; "); }
                let child = pool.children[(ch + i) as usize];
                print_node(pool, child, depth);
            }
        }
    }
}

fn print_indent(depth: u8) {
    for _ in 0..depth { print(b"  "); }
}

fn print_u16(n: u16) {
    if n == u16::MAX { print(b"?"); return; }
    let mut buf = [b'0'; 5];
    let mut i = 5usize;
    let mut v = n;
    if v == 0 { print(b"0"); return; }
    while v > 0 { i -= 1; buf[i] = b'0' + (v % 10) as u8; v /= 10; }
    print(&buf[i..]);
}

fn print_u8(n: u8) {
    let mut buf = [b'0'; 3];
    let mut i = 3usize;
    let mut v = n;
    if v == 0 { print(b"0"); return; }
    while v > 0 { i -= 1; buf[i] = b'0' + (v % 10) as u8; v /= 10; }
    print(&buf[i..]);
}