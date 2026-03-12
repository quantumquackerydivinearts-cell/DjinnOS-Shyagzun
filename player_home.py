# player_home_voxels.py
# Player Home - Voxel Definition for Quantum Quackery Atelier
# Ko's Labyrinth - Game 7

from pathlib import Path
from typing import Dict, Any, List


SCENE_ID = "lapidus/home_morning"
SCENE_NAME = "Alexandria's Cottage"
REALM_ID = "lapidus"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "productions/kos-labyrnth/scenes/lapidus/home_morning.scene.json"

def generate_player_home_voxels() -> Dict[str, Any]:
    """
    Generates the player's starting home in Lapidus.
    Returns complete voxel scene data.
    """
    voxels = []
    
    # DIMENSIONS
    width = 12   # x-axis
    depth = 8    # y-axis  
    height = 6   # z-axis
    
    # FLOOR (z=0, full coverage)
    for x in range(width):
        for y in range(depth):
            voxels.append({
                "x": x,
                "y": y,
                "z": 0,
                "color": "#8B6914",  # Dark goldenrod (wooden planks)
                "color_token": "Ot",  # Orange
                "presence_token": "Ta",
                "material": "wood_floor",
                "walkable": True,
                "solid": False
            })
    
    # WALLS - PERIMETER (z=1 to z=3)
    for z in range(1, 4):
        # North wall (y=0)
        for x in range(width):
            if x in [5, 6]:  # Window gap
                continue
            voxels.append({
                "x": x,
                "y": 0,
                "z": z,
                "color": "#696969",  # Dim gray (stone)
                "color_token": "El",  # Yellow-gray stone
                "presence_token": "Ta",
                "material": "stone_wall",
                "solid": True
            })
        
        # South wall (y=depth-1)
        for x in range(width):
            if z == 1 and x == width // 2:  # Door gap at z=1
                continue
            voxels.append({
                "x": x,
                "y": depth - 1,
                "z": z,
                "color": "#696969",
                "color_token": "El",
                "presence_token": "Ta",
                "material": "stone_wall",
                "solid": True
            })
        
        # West wall (x=0)
        for y in range(depth):
            voxels.append({
                "x": 0,
                "y": y,
                "z": z,
                "color": "#696969",
                "color_token": "El",
                "presence_token": "Ta",
                "material": "stone_wall",
                "solid": True
            })
        
        # East wall (x=width-1)
        for y in range(depth):
            voxels.append({
                "x": width - 1,
                "y": y,
                "z": z,
                "color": "#696969",
                "color_token": "El",
                "presence_token": "Ta",
                "material": "stone_wall",
                "solid": True
            })
    
    # DOOR (red, south wall center, z=1 and z=2)
    door_x = width // 2
    voxels.extend([
        {
            "x": door_x,
            "y": depth - 1,
            "z": 1,
            "color": "#8B0000",  # Dark red
            "color_token": "Ru",
            "presence_token": "Ta",
            "material": "wood_door",
            "interaction": "exit",
            "solid": False
        },
        {
            "x": door_x,
            "y": depth - 1,
            "z": 2,
            "color": "#8B0000",
            "color_token": "Ru",
            "presence_token": "Ta",
            "material": "wood_door",
            "interaction": "exit",
            "solid": False
        }
    ])
    
    # WINDOW (north wall, light blue glass, z=2)
    voxels.extend([
        {
            "x": 5,
            "y": 0,
            "z": 2,
            "color": "#87CEEB",  # Sky blue
            "color_token": "Fu",  # Blue
            "presence_token": "Ta",
            "opacity_token": "Wu",  # Translucent
            "material": "glass",
            "solid": False
        },
        {
            "x": 6,
            "y": 0,
            "z": 2,
            "color": "#87CEEB",
            "color_token": "Fu",
            "presence_token": "Ta",
            "opacity_token": "Wu",
            "material": "glass",
            "solid": False
        }
    ])
    
    # ROOF (simple flat roof, z=4)
    for x in range(width):
        for y in range(depth):
            voxels.append({
                "x": x,
                "y": y,
                "z": 4,
                "color": "#654321",  # Dark brown (thatch)
                "color_token": "Ot",
                "presence_token": "Ta",
                "material": "thatch_roof",
                "solid": True
            })
    
    # ALCHEMY WORKBENCH (west side, 3 wide x 2 deep x 2 high)
    bench_x = 2
    bench_y = 2
    
    # Bench base (z=1)
    for bx in range(3):
        for by in range(2):
            voxels.append({
                "x": bench_x + bx,
                "y": bench_y + by,
                "z": 1,
                "color": "#8B4513",  # Saddle brown
                "color_token": "Ot",
                "presence_token": "Ta",
                "material": "wood_furniture",
                "interaction": "alchemy_bench",
                "solid": True
            })
    
    # Tools on bench (copper/brass colored voxels, z=2)
    voxels.extend([
        {
            "x": bench_x,
            "y": bench_y,
            "z": 2,
            "color": "#B87333",  # Copper
            "color_token": "El",
            "presence_token": "Ta",
            "material": "metal_tool",
            "solid": False
        },
        {
            "x": bench_x + 2,
            "y": bench_y + 1,
            "z": 2,
            "color": "#B87333",
            "color_token": "El",
            "presence_token": "Ta",
            "material": "metal_tool",
            "solid": False
        }
    ])
    
    # FURNACE (east side, 1 wide x 1 deep x 3 high, glowing)
    furn_x = width - 3
    furn_y = depth // 2
    
    for fz in range(1, 4):
        voxels.append({
            "x": furn_x,
            "y": furn_y,
            "z": fz,
            "color": "#FF4500" if fz == 2 else "#8B0000",  # Orange-red glow at middle
            "color_token": "Ru",
            "presence_token": "Ta",
            "material": "furnace",
            "emits_light": fz == 2,
            "light_color": "#FF6600" if fz == 2 else None,
            "interaction": "smelt",
            "solid": True
        })
    
    # BED (northeast corner, 3 wide x 2 deep x 1 high)
    bed_x = width - 4
    bed_y = 1
    
    for bx in range(3):
        for by in range(2):
            voxels.append({
                "x": bed_x + bx,
                "y": bed_y + by,
                "z": 1,
                "color": "#4B0082",  # Indigo (blanket)
                "color_token": "Ka",
                "presence_token": "Ta",
                "material": "cloth",
                "interaction": "rest",
                "solid": True
            })
    
    # CHEST (southwest corner, 2 wide x 1 deep x 1 high)
    voxels.extend([
        {
            "x": 2,
            "y": depth - 2,
            "z": 1,
            "color": "#8B4513",
            "color_token": "Ot",
            "presence_token": "Ta",
            "material": "wood_chest",
            "interaction": "storage",
            "solid": True
        },
        {
            "x": 3,
            "y": depth - 2,
            "z": 1,
            "color": "#8B4513",
            "color_token": "Ot",
            "presence_token": "Ta",
            "material": "wood_chest",
            "interaction": "storage",
            "solid": True
        }
    ])
    
    # MEDITATION CUSHION (center floor, 1 voxel, violet)
    voxels.append({
        "x": width // 2,
        "y": depth // 2,
        "z": 1,
        "color": "#9400D3",  # Dark violet
        "color_token": "AE",
        "presence_token": "Ta",
        "material": "cloth_cushion",
        "interaction": "meditate",
        "solid": False
    })
    
    # BOOKSHELF (north wall interior, 4 wide x 1 deep x 2 high)
    for bx in range(4):
        # Shelf base (z=1)
        voxels.append({
            "x": 4 + bx,
            "y": 1,
            "z": 1,
            "color": "#654321",
            "color_token": "Ot",
            "presence_token": "Ta",
            "material": "wood_shelf",
            "solid": True
        })
        # Books (z=2)
        voxels.append({
            "x": 4 + bx,
            "y": 1,
            "z": 2,
            "color": "#8B4513",
            "color_token": "Ot",
            "presence_token": "Ta",
            "material": "books",
            "interaction": "read",
            "solid": False
        })
    
    # Compile scene data
    scene_data = {
        "scene_id": SCENE_ID,
        "scene_name": SCENE_NAME,
        "scene_type": "voxel_interior",
        "realm_id": REALM_ID,
        "dimensions": {
            "width": width,
            "depth": depth,
            "height": height
        },
        "spawn_point": {
            "x": width // 2,
            "y": depth - 2,
            "z": 1
        },
        "camera_default": {
            "angle": 45,
            "elevation": 30,
            "zoom": 1.0
        },
        "voxels": voxels,
        "interactions": {
            "alchemy_bench": {
                "position": {"x": bench_x, "y": bench_y, "z": 1},
                "action": "open_alchemy_ui",
                "prompt": "Press E to use alchemy workbench"
            },
            "furnace": {
                "position": {"x": furn_x, "y": furn_y, "z": 2},
                "action": "open_smelt_ui",
                "prompt": "Press E to use furnace"
            },
            "rest": {
                "position": {"x": bed_x, "y": bed_y, "z": 1},
                "action": "save_and_heal",
                "prompt": "Press E to rest (saves game)"
            },
            "storage": {
                "position": {"x": 2, "y": depth - 2, "z": 1},
                "action": "open_chest",
                "prompt": "Press E to open chest"
            },
            "meditate": {
                "position": {"x": width // 2, "y": depth // 2, "z": 1},
                "action": "meditation_tutorial",
                "prompt": "Press E to meditate"
            },
            "read": {
                "position": {"x": 4, "y": 1, "z": 2},
                "action": "lore_books",
                "prompt": "Press E to read books"
            },
            "exit": {
                "position": {"x": door_x, "y": depth - 1, "z": 1},
                "action": "exit_to_lapidus_town",
                "prompt": "Press E to go outside"
            }
        },
        "ambient": {
            "music": "home_hearth_theme",
            "time_of_day": "morning",
            "weather": "clear"
        }
    }
    
    return scene_data


def build_player_home_scene_graph(scene: Dict[str, Any]) -> Dict[str, Any]:
    """Build a minimal scene graph from the voxel scene's interaction map."""
    interactions_obj = scene.get("interactions")
    interactions = interactions_obj if isinstance(interactions_obj, dict) else {}
    nodes: List[Dict[str, Any]] = []

    spawn = scene.get("spawn_point")
    if isinstance(spawn, dict):
        nodes.append(
            {
                "node_id": "spawn_point",
                "kind": "spawn",
                "x": float(spawn.get("x", 0)),
                "y": float(spawn.get("y", 0)),
                "metadata": {
                    "z": int(spawn.get("z", 0)),
                    "placement_id": f"{SCENE_ID}:spawn_point",
                },
            }
        )

    for key in sorted(interactions.keys()):
        value = interactions.get(key)
        if not isinstance(value, dict):
            continue
        position = value.get("position")
        if not isinstance(position, dict):
            continue
        nodes.append(
            {
                "node_id": key,
                "kind": "interaction",
                "x": float(position.get("x", 0)),
                "y": float(position.get("y", 0)),
                "metadata": {
                    "z": int(position.get("z", 0)),
                    "placement_id": f"{SCENE_ID}:{key}",
                    "interaction": key,
                    "action": value.get("action"),
                    "prompt": value.get("prompt"),
                },
            }
        )

    return {
        "schema": "atelier.scene.content.v1",
        "scene_id": SCENE_ID,
        "realm_id": REALM_ID,
        "name": SCENE_NAME,
        "description": "Player starting home in Lapidus.",
        "nodes": nodes,
        "edges": [],
        "renderer": {
            "scene": scene,
        },
        "source": {
            "generator": "player_home.py",
        },
    }


# Export function for JSON compatibility
def export_player_home_json():
    """Export voxel scene data as JSON-serializable dict."""
    import json
    scene = generate_player_home_voxels()
    return json.dumps(scene, indent=2)


def export_player_home_scene_json():
    """Export full scene graph payload with embedded voxel scene."""
    import json
    scene = generate_player_home_voxels()
    graph = build_player_home_scene_graph(scene)
    return json.dumps(graph, indent=2)


# Main execution
if __name__ == "__main__":
    scene = generate_player_home_voxels()
    graph = build_player_home_scene_graph(scene)
    print(f"Generated player home with {len(scene['voxels'])} voxels")
    print(f"Dimensions: {scene['dimensions']}")
    print(f"Interactions: {len(scene['interactions'])}")

    # Save to production scene library
    output_path = DEFAULT_OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    output_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(f"Saved to {output_path}")
