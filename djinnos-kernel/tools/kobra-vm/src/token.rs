// Tokenizer.  Delimiters are [ ] { } ( ) ; :
// Everything else is a WORD token (whitespace-separated).

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Tok<'a> {
    LBracket,
    RBracket,
    LBrace,
    RBrace,
    LParen,
    RParen,
    Semi,
    Colon,
    Word(&'a [u8]),
    Eof,
}

pub struct Lexer<'a> {
    src: &'a [u8],
    pos: usize,
    pub peeked: Option<Tok<'a>>,
}

impl<'a> Lexer<'a> {
    pub fn new(src: &'a [u8]) -> Self {
        let mut l = Lexer { src, pos: 0, peeked: None };
        l.peeked = Some(l.next_raw());
        l
    }

    pub fn peek(&self) -> Tok<'a> {
        self.peeked.unwrap_or(Tok::Eof)
    }

    pub fn advance(&mut self) -> Tok<'a> {
        let tok = self.peeked.take().unwrap_or(Tok::Eof);
        self.peeked = Some(self.next_raw());
        tok
    }

    fn next_raw(&mut self) -> Tok<'a> {
        // Skip whitespace
        while self.pos < self.src.len() && self.src[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
        if self.pos >= self.src.len() { return Tok::Eof; }

        let b = self.src[self.pos];
        self.pos += 1;
        match b {
            b'[' => Tok::LBracket,
            b']' => Tok::RBracket,
            b'{' => Tok::LBrace,
            b'}' => Tok::RBrace,
            b'(' => Tok::LParen,
            b')' => Tok::RParen,
            b';' => Tok::Semi,
            b':' => Tok::Colon,
            _   => {
                let start = self.pos - 1;
                while self.pos < self.src.len() {
                    let c = self.src[self.pos];
                    if c.is_ascii_whitespace()
                        || c == b'[' || c == b']'
                        || c == b'{' || c == b'}'
                        || c == b'(' || c == b')'
                        || c == b';' || c == b':'
                    { break; }
                    self.pos += 1;
                }
                Tok::Word(&self.src[start..self.pos])
            }
        }
    }
}