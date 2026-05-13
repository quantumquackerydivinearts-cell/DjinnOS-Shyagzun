import sys
sys.path.insert(0, '.')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../DjinnOS_Shyagzun')

from atelier_api.bok import snapshot_from_kobra, compute_diff
from pathlib import Path

positions = {
    'wiltoll_lane':    ([0.12, 0.44],   5.8, 'bounded'),
    'home_morning':    ([0.0,  0.0],    6.0, 'bounded'),
    'home_apothecary': ([-0.74, 0.18],  7.2, 'edge'),
    'sulphera_entry':  ([-0.6, -0.4],   4.5, 'edge'),
}

def snap(name):
    path = Path(f'../../productions/kos-labyrnth/scenes/lapidus/{name}.scene.ko')
    if not path.exists():
        path = Path(f'../../productions/kos-labyrnth/scenes/sulphera/{name.replace("sulphera_","")}.scene.ko')
    src = path.read_text(encoding='utf-8')
    azoth, coil, bound = positions[name]
    return snapshot_from_kobra(src, tuple(azoth), coil, bound, scene_name=name)

morning    = snap('home_morning')
apothecary = snap('home_apothecary')
sulphera   = snap('sulphera_entry')
lane       = snap('wiltoll_lane')

print("The key question: which transitions are genuine Wunashakoun breaths?")
print()

diffs = [
    ("home_morning    -> home_apothecary", morning,    apothecary),
    ("home_morning    -> sulphera_entry",  morning,    sulphera),
    ("wiltoll_lane    -> home_apothecary", lane,       apothecary),
    ("wiltoll_lane    -> sulphera_entry",  lane,       sulphera),
    ("home_apothecary -> sulphera_entry",  apothecary, sulphera),
]

for label, s, e in diffs:
    d = compute_diff(s, e)
    gained = sorted(d.layers_gained) if d.layers_gained else ['—']
    lost   = sorted(d.layers_lost)   if d.layers_lost   else ['—']
    print(f"  {label}")
    print(f"    azoth_dist={d.azoth_distance:.4f}  boundary={d.boundedness_start}->{d.boundedness_end}")
    print(f"    layers gained={gained}  lost={lost}  sem_dist={d.semantic_distance:.3f}")
    print(f"    is_wunashakoun={d.is_wunashakoun}  depth={d.wunashakoun_depth:.4f}")
    print()
