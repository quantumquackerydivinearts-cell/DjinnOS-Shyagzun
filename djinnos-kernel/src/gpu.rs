// GpuSurface trait — common pixel-drawing interface.
//
// Implemented by VirtIO GpuDriver (RISC-V) and FbDriver (x86_64 linear FB).
// Pixel format: BGR — arguments are (b, g, r) to match the BGRX memory layout
// used by VirtIO.  FbDriver converts to whatever the firmware reports.
//
// set_pixel and fill take &self because both implementations write through
// a raw pointer without modifying struct state.  flush takes &mut self
// because it may update queue indices or similar bookkeeping.

pub trait GpuSurface {
    fn width(&self)  -> u32;
    fn height(&self) -> u32;
    fn set_pixel(&self, x: u32, y: u32, b: u8, g: u8, r: u8);
    fn fill(&self, b: u8, g: u8, r: u8);
    fn flush(&mut self);

    /// Fill a horizontal span [x0, x1) on row y with a solid colour.
    /// This is the inner loop of every span-based rasterizer (isometric
    /// faces, triangles, texture rows).  Backends override this with a
    /// tight contiguous-write loop; the default falls back to set_pixel.
    fn fill_span(&self, x0: u32, x1: u32, y: u32, b: u8, g: u8, r: u8) {
        for x in x0..x1.min(self.width()) {
            self.set_pixel(x, y, b, g, r);
        }
    }

    /// Fill a rectangle by calling fill_span once per row.
    fn fill_rect(&self, x: u32, y: u32, w: u32, h: u32, b: u8, g: u8, r: u8) {
        for row in y..( y + h).min(self.height()) {
            self.fill_span(x, x + w, row, b, g, r);
        }
    }

    /// Copy a row of BGR pixels from `src` onto row y starting at x0.
    fn blit_row(&self, src: &[(u8, u8, u8)], x0: u32, y: u32) {
        let w = self.width();
        for (i, &(b, g, r)) in src.iter().enumerate() {
            let x = x0 + i as u32;
            if x < w { self.set_pixel(x, y, b, g, r); }
        }
    }

    /// Bresenham line from (x0,y0) to (x1,y1).
    fn draw_line(&self, mut x0: i32, mut y0: i32, x1: i32, y1: i32,
                 b: u8, g: u8, r: u8) {
        let dx =  (x1 - x0).abs();
        let dy = -(y1 - y0).abs();
        let sx = if x0 < x1 { 1i32 } else { -1 };
        let sy = if y0 < y1 { 1i32 } else { -1 };
        let mut err = dx + dy;
        let (w, h) = (self.width() as i32, self.height() as i32);
        loop {
            if x0 >= 0 && y0 >= 0 && x0 < w && y0 < h {
                self.set_pixel(x0 as u32, y0 as u32, b, g, r);
            }
            if x0 == x1 && y0 == y1 { break; }
            let e2 = 2 * err;
            if e2 >= dy { err += dy; x0 += sx; }
            if e2 <= dx { err += dx; y0 += sy; }
        }
    }
}
