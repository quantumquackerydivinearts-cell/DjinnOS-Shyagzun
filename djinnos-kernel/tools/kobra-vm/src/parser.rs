// Recursive descent parser.
//
// Grammar (from kobra Python source):
//   sequence     ::= substructure (';' substructure)*
//   substructure ::= application (':' application)?
//   application  ::= primary ('(' sequence ')')*
//   primary      ::= wunashako | group | '(' sequence ')'
//   wunashako    ::= '[' token* ']'
//   group        ::= '{' sequence (';' sequence)* '}'

use crate::ast::{Pool, Node};
use crate::token::{Lexer, Tok};
use crate::sublayer::{segment, MAX_AKINEN};

pub enum ParseResult {
    Ok(u8),
    Err,
    Empty,
}

pub fn parse(src: &[u8], pool: &mut Pool) -> ParseResult {
    let mut lex = Lexer::new(src);
    if lex.peek() == Tok::Eof { return ParseResult::Empty; }
    match parse_seq(&mut lex, pool) {
        Some(idx) => ParseResult::Ok(idx),
        None      => ParseResult::Err,
    }
}

fn parse_seq(lex: &mut Lexer, pool: &mut Pool) -> Option<u8> {
    let first = parse_sub(lex, pool)?;
    let mut kids = [0u8; 32];
    let mut n = 1usize;
    kids[0] = first;

    while lex.peek() == Tok::Semi && n < 32 {
        lex.advance(); // consume ';'
        let next = parse_sub(lex, pool)?;
        kids[n] = next;
        n += 1;
    }

    if n == 1 {
        Some(first)
    } else {
        let (ch, count) = pool.alloc_children(&kids[..n])?;
        pool.alloc(Node::Seq { ch, n: count })
    }
}

fn parse_sub(lex: &mut Lexer, pool: &mut Pool) -> Option<u8> {
    let lhs = parse_app(lex, pool)?;
    if lex.peek() == Tok::Colon {
        lex.advance();
        let rhs = parse_app(lex, pool)?;
        pool.alloc(Node::Sub { lhs, rhs })
    } else {
        Some(lhs)
    }
}

fn parse_app(lex: &mut Lexer, pool: &mut Pool) -> Option<u8> {
    let mut func = parse_primary(lex, pool)?;
    while lex.peek() == Tok::LParen {
        lex.advance(); // consume '('
        let arg = parse_seq(lex, pool)?;
        if lex.peek() != Tok::RParen { return None; }
        lex.advance(); // consume ')'
        func = pool.alloc(Node::Apply { func, arg })?;
    }
    Some(func)
}

fn parse_primary(lex: &mut Lexer, pool: &mut Pool) -> Option<u8> {
    match lex.peek() {
        Tok::LBracket => parse_wunashako(lex, pool),
        Tok::LBrace   => parse_group(lex, pool),
        Tok::LParen   => {
            lex.advance();
            let inner = parse_seq(lex, pool)?;
            if lex.peek() != Tok::RParen { return None; }
            lex.advance();
            Some(inner)
        }
        _ => None,
    }
}

fn parse_wunashako(lex: &mut Lexer, pool: &mut Pool) -> Option<u8> {
    lex.advance(); // consume '['
    let mut kids = [0u8; 64];
    let mut n = 0usize;

    while lex.peek() != Tok::RBracket && lex.peek() != Tok::Eof && n < 64 {
        if let Tok::Word(w) = lex.advance() {
            // Segment the word into akinen
            let (akinen, count) = segment(w);
            for i in 0..count {
                if n >= 64 { break; }
                let ak = akinen[i];
                let node = if ak.addr == u16::MAX {
                    let (s, l) = pool.intern_word(ak.name.as_bytes());
                    Node::Unknown { start: s, len: l }
                } else {
                    Node::Symbol { addr: ak.addr, name: ak.name }
                };
                kids[n] = pool.alloc(node)?;
                n += 1;
            }
        } else {
            break;
        }
    }

    if lex.peek() != Tok::RBracket { return None; }
    lex.advance(); // consume ']'

    let (ch, count) = pool.alloc_children(&kids[..n])?;
    pool.alloc(Node::Wunashako { ch, n: count })
}

fn parse_group(lex: &mut Lexer, pool: &mut Pool) -> Option<u8> {
    lex.advance(); // consume '{'
    let mut kids = [0u8; 32];
    let mut n = 0usize;

    let first = parse_seq(lex, pool)?;
    if n < 32 { kids[n] = first; n += 1; }

    while lex.peek() == Tok::Semi && n < 32 {
        lex.advance();
        let next = parse_seq(lex, pool)?;
        kids[n] = next;
        n += 1;
    }

    if lex.peek() != Tok::RBrace { return None; }
    lex.advance(); // consume '}'

    let (ch, count) = pool.alloc_children(&kids[..n])?;
    pool.alloc(Node::Group { ch, n: count })
}