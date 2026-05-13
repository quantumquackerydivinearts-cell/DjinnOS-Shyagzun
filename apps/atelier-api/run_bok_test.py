import sys
sys.path.insert(0, '.')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../DjinnOS_Shyagzun')

from atelier_api.bok import snapshot_from_kobra, compute_diff
from pathlib import Path

scenes = {
    'wiltoll_lane':    Path('../../productions/kos-labyrnth/scenes/lapidus/wiltoll_lane.scene.ko'),
    'home_morning':    Path('../../productions/kos-labyrnth/scenes/lapidus/home_morning.scene.ko'),
    'home_apothecary': Path('../../productions/kos-labyrnth/scenes/lapidus/home_apothecary.scene.ko'),
    'sulphera_entry':  Path('../../productions/kos-labyrnth/scenes/sulphera/entry.scene.ko'),
}

# Simulated practice positions per scene
positions = {
    'wiltoll_lane':    ([0.12, 0.44],   5.8, 'bounded'),
    'home_morning':    ([0.0,  0.0],    6.0, 'bounded'),
    'home_apothecary': ([-0.74, 0.18],  7.2, 'edge'),
    'sulphera_entry':  ([-0.6, -0.4],   4.5, 'edge'),
}

snaps = {}
for name, path in scenes.items():
    src = path.read_text(encoding='utf-8')
    azoth, coil, bound = positions[name]
    snap = snapshot_from_kobra(src, tuple(azoth), coil, bound, scene_name=name)
    snaps[name] = snap

    fired = sorted(snap.fired_layers) if snap.fired_layers else ['none']
    dom   = snap.dominant_crossing or 'none'
    sig   = snap.elemental_sig

    print(f"=== {name} ===")
    print(f"  Boundedness:        {snap.boundedness}")
    print(f"  Fired layers:       {fired}")
    print(f"  Dominant crossing:  {dom}")
    print(f"  Elemental:          Shak={sig['Shak']:.2f}  Puf={sig['Puf']:.2f}  Mel={sig['Mel']:.2f}  Zot={sig['Zot']:.2f}")
    print(f"  Crossing entropy:   {snap.crossing_entropy:.4f} bits")
    print(f"  Field energy:       {snap.field_energy:.1f}")
    print(f"  Wunashakoun signal: {snap.wunashakoun_signal:.4f}")
    print()

print("=== DIFF: wiltoll_lane -> home_apothecary ===")
d1 = compute_diff(snaps['wiltoll_lane'], snaps['home_apothecary'])
print(f"  Azoth distance:    {d1.azoth_distance:.4f}")
print(f"  Boundedness:       {d1.boundedness_start} -> {d1.boundedness_end}")
gained1 = sorted(d1.layers_gained) if d1.layers_gained else ['none']
lost1   = sorted(d1.layers_lost)   if d1.layers_lost   else ['none']
print(f"  Layers gained:     {gained1}")
print(f"  Layers lost:       {lost1}")
print(f"  Semantic distance: {d1.semantic_distance:.4f}")
print(f"  Dominant shift:    {d1.dominant_shift}")
print(f"  Is Wunashakoun:    {d1.is_wunashakoun}")
print(f"  Wunashakoun depth: {d1.wunashakoun_depth:.4f}")
print()

print("=== DIFF: home_apothecary -> sulphera_entry ===")
d2 = compute_diff(snaps['home_apothecary'], snaps['sulphera_entry'])
print(f"  Azoth distance:    {d2.azoth_distance:.4f}")
print(f"  Boundedness:       {d2.boundedness_start} -> {d2.boundedness_end}")
gained2 = sorted(d2.layers_gained) if d2.layers_gained else ['none']
lost2   = sorted(d2.layers_lost)   if d2.layers_lost   else ['none']
print(f"  Layers gained:     {gained2}")
print(f"  Layers lost:       {lost2}")
print(f"  Semantic distance: {d2.semantic_distance:.4f}")
print(f"  Dominant shift:    {d2.dominant_shift}")
print(f"  Is Wunashakoun:    {d2.is_wunashakoun}")
print(f"  Wunashakoun depth: {d2.wunashakoun_depth:.4f}")
