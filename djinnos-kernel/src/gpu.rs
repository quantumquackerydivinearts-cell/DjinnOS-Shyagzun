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

    /// Fill a rectangle (x, y, w, h) with a solid colour.
    /// Provided by each backend with volatile writes so LTO/−Oz cannot
    /// miscompile the pixel-address computation into Shell::render's frame.
    fn fill_rect(&self, x: u32, y: u32, w: u32, h: u32, b: u8, g: u8, r: u8) {
        let x1 = x + w;
        let y1 = y + h;
        for row in y..y1 {
            for col in x..x1 {
                self.set_pixel(col, row, b, g, r);
            }
        }
    }
}
