// AST — fixed-size arena, no heap.
//
// Grammar:
//   sequence     ::= substructure (';' substructure)*
//   substructure ::= application (':' application)?
//   application  ::= primary ('(' sequence ')')*
//   primary      ::= wunashako | group | '(' sequence ')'
//   wunashako    ::= '[' token* ']'
//   group        ::= '{' sequence (';' sequence)* '}'

pub const MAX_NODES:    usize = 128;
pub const MAX_CHILDREN: usize = 256;

#[derive(Clone, Copy)]
pub enum Node {
    /// Single recognized symbol from the byte table.
    Symbol { addr: u16, name: &'static str },
    /// Unrecognized word token (carries the raw byte slice).
    Unknown { start: u8, len: u8 },  // indices into a word buffer in Pool
    /// [ akinen* ] — a chord.
    Wunashako { ch: u8, n: u8 },
    /// { sequence; sequence; ... } — parallel execution.
    Group { ch: u8, n: u8 },
    /// f(arg)
    Apply { func: u8, arg: u8 },
    /// lhs:rhs
    Sub { lhs: u8, rhs: u8 },
    /// a ; b ; c
    Seq { ch: u8, n: u8 },
}

pub struct Pool {
    pub nodes:      [Node; MAX_NODES],
    pub node_count: usize,
    pub children:   [u8; MAX_CHILDREN],
    pub ch_count:   usize,
    /// Flat storage for raw unknown words (each word ≤32 bytes, up to 32 words).
    pub words:      [[u8; 32]; 32],
    pub word_count: usize,
}

impl Pool {
    pub const fn empty() -> Self {
        Pool {
            nodes:      [Node::Symbol { addr: 0, name: "" }; MAX_NODES],
            node_count: 0,
            children:   [0u8; MAX_CHILDREN],
            ch_count:   0,
            words:      [[0u8; 32]; 32],
            word_count: 0,
        }
    }

    pub fn reset(&mut self) {
        self.node_count = 0;
        self.ch_count   = 0;
        self.word_count = 0;
    }

    /// Allocate a node slot, return its index.
    pub fn alloc(&mut self, n: Node) -> Option<u8> {
        if self.node_count >= MAX_NODES { return None; }
        let idx = self.node_count as u8;
        self.nodes[self.node_count] = n;
        self.node_count += 1;
        Some(idx)
    }

    /// Allocate a run of child indices from the children array.
    /// Returns (start, count) where start is the index into `children`.
    pub fn alloc_children(&mut self, kids: &[u8]) -> Option<(u8, u8)> {
        if self.ch_count + kids.len() > MAX_CHILDREN { return None; }
        let start = self.ch_count as u8;
        for &k in kids { self.children[self.ch_count] = k; self.ch_count += 1; }
        Some((start, kids.len() as u8))
    }

    /// Store a raw word (unrecognized token), return (start_idx, len).
    pub fn intern_word(&mut self, w: &[u8]) -> (u8, u8) {
        if self.word_count >= 32 { return (0, 0); }
        let idx = self.word_count;
        let n = w.len().min(31);
        self.words[idx][..n].copy_from_slice(&w[..n]);
        self.word_count += 1;
        (idx as u8, n as u8)
    }

    pub fn get(&self, idx: u8) -> Node {
        self.nodes[idx as usize]
    }
}

/// Collect all Symbol addresses reachable from node `idx`.
pub fn collect_addresses(pool: &Pool, idx: u8, out: &mut [u16; 64], count: &mut usize) {
    match pool.get(idx) {
        Node::Symbol { addr, .. } => {
            if *count < 64 { out[*count] = addr; *count += 1; }
        }
        Node::Unknown { .. } => {}
        Node::Wunashako { ch, n } | Node::Group { ch, n } | Node::Seq { ch, n } => {
            for i in 0..n {
                let child = pool.children[(ch + i) as usize];
                collect_addresses(pool, child, out, count);
            }
        }
        Node::Apply { func, arg } => {
            collect_addresses(pool, func, out, count);
            collect_addresses(pool, arg,  out, count);
        }
        Node::Sub { lhs, rhs } => {
            collect_addresses(pool, lhs, out, count);
            collect_addresses(pool, rhs, out, count);
        }
    }
}