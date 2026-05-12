// sprite.rs — 2D entity sprites overlaid on the voxel world.
//
// Characters are flat 2D tokens drawn ON TOP of the voxel layer at their
// iso-projected world position.  This is the Octopath "pop-up book" aesthetic:
// the world is 3D voxels; entities are flat sprites that face the camera.
//
// Sprite dimensions scale with the active CannabisMode tile size:
//   width  = tile_px
//   height = tile_px * 3 / 2  (portrait ratio)
//
// The sprite's "foot" sits at the top face centre of the entity's ground voxel.
// A small drop-shadow ellipse is drawn under the feet (painter's algorithm: drawn
// before the sprite so it appears beneath).
//
// For alpha: sprites are solid-color rectangles with a 1-pixel darker outline.
// A simple head/body split provides minimal character read:
//   top  quarter → HEAD_FRAC (head, slightly lighter color)
//   rest          → body fill color

use crate::gpu::GpuSurface;
use crate::voxel::{iso_x, iso_y, Camera};

// ── Shadow ellipse ────────────────────────────────────────────────────────────

fn draw_shadow(gpu: &dyn GpuSurface, cx: i32, cy: i32, rx: i32, ry: i32,
               sw: u32, sh: u32)
{
    if ry <= 0 { return; }
    for dy in -ry..=ry {
        let t = dy * 1024 / ry.max(1);          // fixed-point sin²-like scale
        let half_w = (rx * rx - (t * rx / 1024) * (t * rx / 1024)).max(0);
        // fast integer sqrt approximation (Newton step)
        let mut s = (half_w as u32).isqrt();
        if s == 0 { continue; }
        let sx0 = cx - s as i32;
        let sy  = cy + dy;
        if sy < 0 || sy >= sh as i32 { continue; }
        let x0 = sx0.max(0) as u32;
        let x1 = (sx0 + s as i32 * 2).min(sw as i32).max(0) as u32;
        if x0 < x1 {
            gpu.fill_span(x0, x1, sy as u32, 8, 8, 8); // near-black shadow
        }
    }
}

// ── Sprite render ─────────────────────────────────────────────────────────────

/// Render a single entity sprite at world position (wx, wy, wz).
///
/// `fill`   — (B,G,R) body color.
/// `outline` — (B,G,R) 1-pixel border (usually darker).
pub fn render_sprite(
    gpu:     &dyn GpuSurface,
    camera:  &Camera,
    wx: i32, wy: i32, wz: i32,
    fill:    (u8, u8, u8),
    outline: (u8, u8, u8),
) {
    let sw = gpu.width();
    let sh = gpu.height();
    let tw = camera.mode.tile_px();
    let th = tw / 2;
    let zs = camera.mode.zscale();

    let cam_wx = camera.wx / 256;
    let cam_wz = camera.wz / 256;
    let rx = wx - cam_wx;
    let rz = wz - cam_wz;

    // Iso position of the TOP FACE of the voxel beneath the entity.
    let ox = camera.sx as i32 + iso_x(rx, rz, tw);
    let oy = camera.sy as i32 + iso_y(rx, wy, rz, th, zs);

    // Sprite dimensions.
    let sp_w = tw as i32;
    let sp_h = (tw * 3 / 2) as i32;

    // Sprite foot is at the vertical mid-point of the top face (oy + th/2).
    // Sprite rises upward from there.
    let foot_y = oy + th as i32 / 2;
    let top_y  = foot_y - sp_h;
    let left_x = ox + sp_w / 4;   // centered on the diamond top face

    // Off-screen cull.
    if left_x + sp_w < 0 || left_x > sw as i32 { return; }
    if top_y + sp_h < 0  || top_y  > sh as i32 { return; }

    // Shadow ellipse (rx, ry in pixels).
    let shadow_rx = sp_w / 3;
    let shadow_ry = (sp_w / 6).max(1);
    draw_shadow(gpu, left_x + sp_w / 2, foot_y, shadow_rx, shadow_ry, sw, sh);

    // Head fraction: top 28% of sprite height.
    let head_h  = sp_h * 28 / 100;
    let body_y0 = top_y + head_h;

    // Slightly brighter head color.
    let head_fill = (
        fill.0.saturating_add(20),
        fill.1.saturating_add(20),
        fill.2.saturating_add(20),
    );

    for py in top_y..top_y + sp_h {
        if py < 0 || py >= sh as i32 { continue; }
        let col = if py < body_y0 { head_fill } else { fill };

        let x0 = left_x.max(0) as u32;
        let x1 = (left_x + sp_w).min(sw as i32).max(0) as u32;
        if x0 >= x1 { continue; }

        // Top/bottom border rows → outline color.
        if py == top_y || py == top_y + sp_h - 1 {
            gpu.fill_span(x0, x1, py as u32, outline.0, outline.1, outline.2);
        } else {
            // Left border pixel.
            let bx0 = x0;
            let bx1 = (x0 + 1).min(x1);
            gpu.fill_span(bx0, bx1, py as u32, outline.0, outline.1, outline.2);
            // Interior fill.
            if bx1 < x1 {
                let inner_x1 = if (left_x + sp_w - 1) < sw as i32 {
                    (x1 - 1).max(bx1)
                } else { x1 };
                if bx1 < inner_x1 {
                    gpu.fill_span(bx1, inner_x1, py as u32, col.0, col.1, col.2);
                }
                // Right border pixel.
                if inner_x1 < x1 {
                    gpu.fill_span(inner_x1, x1, py as u32,
                                  outline.0, outline.1, outline.2);
                }
            }
        }
    }
}

// ── Convenience wrappers ──────────────────────────────────────────────────────

pub fn render_player(gpu: &dyn GpuSurface, camera: &Camera,
                     wx: i32, wy: i32, wz: i32)
{
    render_sprite(gpu, camera, wx, wy, wz,
        crate::renderer_bridge::PLAYER_FILL,
        crate::renderer_bridge::PLAYER_SHADOW);
}

pub fn render_npc(gpu: &dyn GpuSurface, camera: &Camera,
                  wx: i32, wy: i32, wz: i32)
{
    render_sprite(gpu, camera, wx, wy, wz,
        crate::renderer_bridge::NPC_FILL,
        crate::renderer_bridge::NPC_OUTLINE);
}
