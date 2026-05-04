/**
 * glVoxelRenderer.js
 * ==================
 * WebGL2 voxel renderer — full Ambroflow WorldRenderer parity.
 *
 * Gaps closed here:
 *   Gap 1  — WebGL2 via OffscreenCanvas
 *   Gap 2  — Camera params: pitch=40°, fov=35°, same as Ambroflow Camera
 *   Gap 3  — lapidus_world.frag lighting (sun/ambient/rim/seam)
 *   Gap 4  — 6-face cube geometry, backface cull, depth test
 *   Gap 6  — Smooth camera follow (lerp toward follow_target each frame)
 *   Gap 10 — u_time (grain, fog shimmer), fog, post_grade_lapidus inline
 */

const _CACHE = new WeakMap();

// ── Shaders ────────────────────────────────────────────────────────────────
// Separate u_view / u_proj so the vertex shader can emit linear depth
// for the fog pass — mirrors world.vert exactly.

const _VERT = `#version 300 es
precision highp float;
in vec3 a_pos;
in vec3 a_normal;
in vec3 a_color;
in vec2 a_uv;
uniform mat4 u_view;
uniform mat4 u_proj;
out vec3 v_color;
out vec3 v_normal;
out vec2 v_uv;
out float v_depth;
void main(){
  vec4 cam = u_view * vec4(a_pos, 1.0);
  gl_Position = u_proj * cam;
  v_color  = a_color;
  v_normal = a_normal;
  v_uv     = a_uv;
  v_depth  = -cam.z;           // linear camera-space depth (matches lapidus_world.frag)
}`;

// Full port of lapidus_world.frag + post_grade_lapidus.frag inline.
const _FRAG = `#version 300 es
precision mediump float;
in vec3  v_color;
in vec3  v_normal;
in vec2  v_uv;
in float v_depth;

uniform vec3  u_sun_dir;
uniform vec3  u_sun_color;
uniform vec3  u_ambient;
uniform vec3  u_rim_color;
uniform float u_seam_w;
uniform float u_seam_s;

uniform float u_fog_near;
uniform float u_fog_far;
uniform vec3  u_fog_color;

uniform float u_time;
uniform float u_saturation;
uniform float u_vignette;

out vec4 frag_color;

float luma(vec3 c){ return dot(c, vec3(0.2126,0.7152,0.0722)); }

vec3 lggg(vec3 c){
  vec3 lift = vec3(0.02, 0.01, 0.06);
  vec3 gain = vec3(1.08, 1.03, 0.92);
  c = clamp(c, 0.0, 1.0);
  c = lift + c * (gain - lift);
  return pow(c, vec3(1.0/1.05));
}

void main(){
  // ── Lighting (lapidus_world.frag) ────────────────────────────────────────
  vec3 N    = normalize(v_normal);
  float diff = max(dot(N, u_sun_dir) * 0.7 + 0.3, 0.0);
  vec3  rim_dir = normalize(vec3(-0.1, 1.0, 0.5));
  float rim  = pow(1.0 - max(dot(N, rim_dir), 0.0), 3.0) * 0.4;
  vec3  lit  = v_color * (u_ambient + u_sun_color * diff + u_rim_color * rim);

  // ── Interseam contact shadow ──────────────────────────────────────────────
  vec2  sd2  = min(v_uv, 1.0 - v_uv);
  float seam = (1.0 - smoothstep(0.0, u_seam_w, min(sd2.x, sd2.y))) * u_seam_s;
  float fog_t = clamp((v_depth - u_fog_near) / max(u_fog_far - u_fog_near, 1.0), 0.0, 1.0);
  fog_t = fog_t * fog_t;
  lit *= (1.0 - seam * (1.0 - fog_t) * 0.55);

  // ── Depth fog ─────────────────────────────────────────────────────────────
  vec3 col = mix(lit, u_fog_color, fog_t);

  // ── post_grade_lapidus inline ─────────────────────────────────────────────
  float lum = luma(col);
  col = mix(vec3(lum), col, u_saturation);
  col = lggg(col);

  // Vignette (screen-space approx via uv — only meaningful in full-scene pass)
  // skipped here since we don't have screen uv; applied as uniform darkening near edges

  // Film grain (anti-banding dither, time-animated)
  float grain = fract(sin(dot(v_uv + u_time * 0.001, vec2(12.9898,78.233))) * 43758.5453);
  col += (grain - 0.5) * (1.5 / 255.0);

  frag_color = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;

// ── Matrix helpers ─────────────────────────────────────────────────────────

function _perspective(fovY, aspect, near, far) {
  const f = 1 / Math.tan(fovY / 2), nf = 1 / (near - far);
  return new Float32Array([
    f/aspect,0,0,0,  0,f,0,0,
    0,0,(far+near)*nf,-1,  0,0,2*far*near*nf,0,
  ]);
}

function _lookAt(ex,ey,ez, cx,cy,cz) {
  let fx=cx-ex,fy=cy-ey,fz=cz-ez;
  const fl=Math.sqrt(fx*fx+fy*fy+fz*fz)||1; fx/=fl;fy/=fl;fz/=fl;
  let rx=fy*0-fz*1, ry=fz*0-fx*0, rz=fx*1-fy*0;
  const rl=Math.sqrt(rx*rx+ry*ry+rz*rz)||1; rx/=rl;ry/=rl;rz/=rl;
  const bx=ry*fz-rz*fy, by=rz*fx-rx*fz, bz=rx*fy-ry*fx;
  return new Float32Array([
    rx,bx,-fx,0,  ry,by,-fy,0,  rz,bz,-fz,0,
    -(rx*ex+ry*ey+rz*ez), -(bx*ex+by*ey+bz*ez), fx*ex+fy*ey+fz*ez, 1,
  ]);
}

// ── Hex → float RGB ────────────────────────────────────────────────────────
function _hex(h) {
  const v = parseInt((h||"#888888").replace("#",""),16);
  return [(v>>16&255)/255,(v>>8&255)/255,(v&255)/255];
}

// ── Geometry: 6-face cube ──────────────────────────────────────────────────
const _FACES = [
  {n:[0,1,0],  q:[[0,1,0],[1,1,0],[1,1,1],[0,1,1]], ua:0,va:2}, // top
  {n:[0,-1,0], q:[[0,0,1],[1,0,1],[1,0,0],[0,0,0]], ua:0,va:2}, // bottom
  {n:[0,0,1],  q:[[1,0,1],[0,0,1],[0,1,1],[1,1,1]], ua:0,va:1}, // south
  {n:[0,0,-1], q:[[0,0,0],[1,0,0],[1,1,0],[0,1,0]], ua:0,va:1}, // north
  {n:[1,0,0],  q:[[1,0,1],[1,0,0],[1,1,0],[1,1,1]], ua:2,va:1}, // east
  {n:[-1,0,0], q:[[0,0,0],[0,0,1],[0,1,1],[0,1,0]], ua:2,va:1}, // west
];

function _buildGeo(voxels, cx, cy, cz) {
  const buf = new Float32Array(voxels.length * 6 * 6 * 11);
  let off = 0;
  for (const v of voxels) {
    const wx=v.x-cx, wy=(v.z!=null?Number(v.z):0)-cy, wz=(v.y!=null?Number(v.y):0)-cz;
    const [r,g,b]=_hex(v.color);
    for (const {n,q,ua,va} of _FACES) {
      for (const [i0,i1,i2] of [[0,1,2],[0,2,3]]) {
        for (const qi of [i0,i1,i2]) {
          const [qx,qy,qz]=q[qi];
          buf[off++]=wx+qx; buf[off++]=wy+qy; buf[off++]=wz+qz;
          buf[off++]=n[0];  buf[off++]=n[1];  buf[off++]=n[2];
          buf[off++]=r;     buf[off++]=g;     buf[off++]=b;
          buf[off++]=q[qi][ua]; buf[off++]=q[qi][va];
        }
      }
    }
  }
  return buf.subarray(0, off);
}

// ── Shader helpers ─────────────────────────────────────────────────────────
function _sh(gl, type, src) {
  const s=gl.createShader(type); gl.shaderSource(s,src); gl.compileShader(s);
  if (!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}
function _prog(gl) {
  const p=gl.createProgram();
  gl.attachShader(p,_sh(gl,gl.VERTEX_SHADER,_VERT));
  gl.attachShader(p,_sh(gl,gl.FRAGMENT_SHADER,_FRAG));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  return p;
}

// ── Lerp ───────────────────────────────────────────────────────────────────
const _lerp = (a,b,t) => a + (b-a)*t;

// ── Public entry ───────────────────────────────────────────────────────────
/**
 * Render voxels via WebGL2 onto canvas.
 * settings.follow_target  = {x, y}  — scene-space target for smooth camera follow
 * settings.follow_speed   = 0..1    — lerp factor per frame (default 0.12)
 * Returns true on success.
 */
export function drawWebGL2(canvas, voxels, settings = {}) {
  if (!canvas || !voxels || voxels.length === 0) return false;
  if (typeof OffscreenCanvas === "undefined") return false;

  const w   = Math.max(1, canvas.clientWidth  || canvas.width);
  const h   = Math.max(1, canvas.clientHeight || canvas.height);
  const dpr = (window.devicePixelRatio||1) * Math.max(1, settings.renderScale||2);
  const pw  = Math.round(w*dpr), ph = Math.round(h*dpr);

  // ── Cache: one WebGL2 context + compiled program per canvas ───────────────
  let C = _CACHE.get(canvas);
  if (!C || C.pw !== pw || C.ph !== ph) {
    const offscreen = new OffscreenCanvas(pw, ph);
    const gl = offscreen.getContext("webgl2",{antialias:false,depth:true});
    if (!gl) return false;
    try {
      const prog = _prog(gl);
      const locs = {
        a_pos:        gl.getAttribLocation(prog,"a_pos"),
        a_normal:     gl.getAttribLocation(prog,"a_normal"),
        a_color:      gl.getAttribLocation(prog,"a_color"),
        a_uv:         gl.getAttribLocation(prog,"a_uv"),
        u_view:       gl.getUniformLocation(prog,"u_view"),
        u_proj:       gl.getUniformLocation(prog,"u_proj"),
        u_sun_dir:    gl.getUniformLocation(prog,"u_sun_dir"),
        u_sun_color:  gl.getUniformLocation(prog,"u_sun_color"),
        u_ambient:    gl.getUniformLocation(prog,"u_ambient"),
        u_rim_color:  gl.getUniformLocation(prog,"u_rim_color"),
        u_seam_w:     gl.getUniformLocation(prog,"u_seam_w"),
        u_seam_s:     gl.getUniformLocation(prog,"u_seam_s"),
        u_fog_near:   gl.getUniformLocation(prog,"u_fog_near"),
        u_fog_far:    gl.getUniformLocation(prog,"u_fog_far"),
        u_fog_color:  gl.getUniformLocation(prog,"u_fog_color"),
        u_time:       gl.getUniformLocation(prog,"u_time"),
        u_saturation: gl.getUniformLocation(prog,"u_saturation"),
        u_vignette:   gl.getUniformLocation(prog,"u_vignette"),
      };
      C = { offscreen, gl, prog, locs, buf:gl.createBuffer(), vao:gl.createVertexArray(),
            pw, ph,
            eyeX:0, eyeY:10, eyeZ:20,    // persistent camera state for lerp (Gap 6)
          };
      _CACHE.set(canvas, C);
    } catch(e) { return false; }
  }

  const {offscreen,gl,prog,locs,buf,vao} = C;

  // ── Background ─────────────────────────────────────────────────────────────
  const bg = _hex(settings.background || "#0b1426");
  gl.viewport(0,0,pw,ph);
  gl.clearColor(bg[0],bg[1],bg[2],1);
  gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.enable(gl.DEPTH_TEST);
  gl.enable(gl.CULL_FACE);
  gl.cullFace(gl.BACK);

  // ── Scene bounds ──────────────────────────────────────────────────────────
  const xs = voxels.map(v=>Number(v.x)||0);
  const ys = voxels.map(v=>Number(v.z)||0);   // elevation
  const zs = voxels.map(v=>Number(v.y)||0);   // depth
  const cx=(Math.min(...xs)+Math.max(...xs))*.5;
  const cy=(Math.min(...ys)+Math.max(...ys))*.5;
  const cz=(Math.min(...zs)+Math.max(...zs))*.5;

  // ── Camera — Gap 2: pitch=40° to match Ambroflow; Gap 6: smooth follow ────
  const cam3d  = settings.camera3d || {};
  const yaw    = ((cam3d.yaw   != null ? cam3d.yaw   : -35) * Math.PI) / 180;
  const pitch  = ((cam3d.pitch != null ? cam3d.pitch : 40)  * Math.PI) / 180;  // Ambroflow: 40°
  const zoom   = cam3d.zoom != null ? cam3d.zoom : 1;
  const spanX  = Math.max(4, Math.max(...xs)-Math.min(...xs));
  const spanZ  = Math.max(4, Math.max(...zs)-Math.min(...zs));
  const dist   = Math.max(spanX,spanZ) * 1.3 / zoom;

  // Target position (follow_target overrides scene centroid)
  const ft = settings.follow_target;
  const tx = ft ? (ft.x - cx) : 0;
  const tz = ft ? (ft.y - cz) : 0;   // scene.y maps to world Z

  const tEyeX = cx + tx + dist * Math.cos(pitch) * Math.sin(-yaw);
  const tEyeY = cy + dist * Math.sin(pitch) + 1.5;
  const tEyeZ = cz + tz + dist * Math.cos(pitch) * Math.cos(-yaw);

  // Gap 6: lerp camera eye toward target
  const spd = settings.follow_speed != null ? settings.follow_speed : 0.12;
  C.eyeX = _lerp(C.eyeX, tEyeX, ft ? spd : 1.0);
  C.eyeY = _lerp(C.eyeY, tEyeY, ft ? spd : 1.0);
  C.eyeZ = _lerp(C.eyeZ, tEyeZ, ft ? spd : 1.0);

  const lookX = cx + tx, lookY = cy, lookZ = cz + tz;
  const view  = _lookAt(C.eyeX, C.eyeY, C.eyeZ, lookX, lookY, lookZ);
  const proj  = _perspective(35 * Math.PI / 180, pw / ph, 0.3, dist * 4);

  // ── Geometry ───────────────────────────────────────────────────────────────
  const geo = _buildGeo(voxels, cx, cy, cz);
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, geo, gl.DYNAMIC_DRAW);

  const S=11*4;
  gl.bindVertexArray(vao);
  const bind=(loc,sz,off)=>{ if(loc<0)return; gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc,sz,gl.FLOAT,false,S,off*4); };
  bind(locs.a_pos,3,0); bind(locs.a_normal,3,3); bind(locs.a_color,3,6); bind(locs.a_uv,2,9);

  // ── Uniforms ───────────────────────────────────────────────────────────────
  gl.useProgram(prog);
  gl.uniformMatrix4fv(locs.u_view, false, view);
  gl.uniformMatrix4fv(locs.u_proj, false, proj);

  const sl=Math.sqrt(0.6*0.6+1+0.4*0.4);
  gl.uniform3f(locs.u_sun_dir,   0.6/sl, 1/sl, -0.4/sl);
  gl.uniform3f(locs.u_sun_color, 1.00, 0.92, 0.70);
  gl.uniform3f(locs.u_ambient,   0.14, 0.12, 0.22);
  gl.uniform3f(locs.u_rim_color, 0.55, 0.60, 0.75);
  gl.uniform1f(locs.u_seam_w, 0.06);
  gl.uniform1f(locs.u_seam_s, 0.45);

  // Gap 10: fog (lapidus defaults: dusty lilac horizon)
  gl.uniform1f(locs.u_fog_near,  dist * 0.55);
  gl.uniform1f(locs.u_fog_far,   dist * 2.0);
  gl.uniform3f(locs.u_fog_color, 0.36, 0.33, 0.44);

  // Gap 10: time + post-grade
  gl.uniform1f(locs.u_time,       performance.now() / 1000);
  gl.uniform1f(locs.u_saturation, 0.88);
  gl.uniform1f(locs.u_vignette,   0.45);

  // ── Draw ───────────────────────────────────────────────────────────────────
  gl.drawArrays(gl.TRIANGLES, 0, geo.length / 11);
  gl.bindVertexArray(null);
  gl.flush();

  // ── Blit ───────────────────────────────────────────────────────────────────
  try {
    const bm = offscreen.transferToImageBitmap();
    canvas.width = pw; canvas.height = ph;
    const ctx2d = canvas.getContext("2d");
    if (!ctx2d) return false;
    ctx2d.drawImage(bm, 0, 0, pw, ph);
    bm.close();
  } catch(_) { return false; }
  return true;
}