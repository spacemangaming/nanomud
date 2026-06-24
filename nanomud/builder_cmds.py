import uuid
from typing import Any
from .models import Room, Item, NPC
from .colors import ansi_format

def parse_value(val: str) -> Any:
    val_lower = val.lower().strip()
    if val_lower == "true":
        return True
    if val_lower == "false":
        return False
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val.strip()

def handle_dig(engine, player, args: str):
    if not args:
        player.send("Usage: @dig <direction> <room_name>")
        return
        
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        player.send("Usage: @dig <direction> <room_name>")
        return
        
    direction = parts[0].lower().strip()
    room_name = parts[1].strip()
    
    aliases = {
        "n": "north", "s": "south", "e": "east", "w": "west",
        "u": "up", "d": "down"
    }
    direction = aliases.get(direction, direction)
    
    # Generate unique room ID
    base_id = room_name.lower().replace(" ", "_")
    room_id = base_id
    while room_id in engine.world.rooms:
        room_id = f"{base_id}_{uuid.uuid4().hex[:4]}"
        
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        player.send("{rYou are not in a valid room!{x")
        return
        
    if direction in current_room.exits:
        player.send(f"Current room already has an exit to the {direction}.")
        return
        
    # Create target room
    new_room = Room(room_id=room_id, name=room_name, desc=f"A newly dug room named {room_name}.")
    
    # Create bidirectional exits
    opposites = {
        "north": "south", "south": "north",
        "east": "west", "west": "east",
        "up": "down", "down": "up"
    }
    opposite_dir = opposites.get(direction, "somewhere")
    
    current_room.exits[direction] = room_id
    new_room.exits[opposite_dir] = current_room.id
    
    engine.world.rooms[room_id] = new_room
    engine.world.save()
    
    player.send(f"You dig {direction} and create a new room: {{C{room_name}{{x (ID: {room_id})")
    current_room.broadcast(f"{{b{player.name}{{x waves a magic builder wand, digging an exit to the {direction}.", exclude=player)

def handle_link(engine, player, args: str):
    if not args:
        player.send("Usage: @link <direction> <existing_room_id>")
        return
        
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        player.send("Usage: @link <direction> <existing_room_id>")
        return
        
    direction = parts[0].lower().strip()
    target_id = parts[1].lower().strip()
    
    aliases = {
        "n": "north", "s": "south", "e": "east", "w": "west",
        "u": "up", "d": "down"
    }
    direction = aliases.get(direction, direction)
    
    if target_id not in engine.world.rooms:
        player.send(f"Room ID '{target_id}' does not exist.")
        return
        
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    current_room.exits[direction] = target_id
    engine.world.save()
    
    player.send(f"You link {direction} to room ID '{target_id}'.")
    current_room.broadcast(f"{{b{player.name}{{x links an exit to the {direction}.", exclude=player)

def handle_unlink(engine, player, args: str):
    if not args:
        player.send("Usage: @unlink <direction>")
        return
        
    direction = args.lower().strip()
    aliases = {
        "n": "north", "s": "south", "e": "east", "w": "west",
        "u": "up", "d": "down"
    }
    direction = aliases.get(direction, direction)
    
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    if direction not in current_room.exits:
        player.send(f"No exit found in direction '{direction}'.")
        return
        
    del current_room.exits[direction]
    engine.world.save()
    
    player.send(f"You unlink exit to the {direction}.")
    current_room.broadcast(f"{{b{player.name}{{x unlinks the exit to the {direction}.", exclude=player)

def handle_roomname(engine, player, args: str):
    if not args:
        player.send("Usage: @roomname <new_name>")
        return
        
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    old_name = current_room.name
    current_room.name = args.strip()
    engine.world.save()
    
    player.send(f"Room renamed to: {{C{current_room.name}{{x")
    current_room.broadcast(f"{{b{player.name}{{x renames the room from '{old_name}' to '{{C{current_room.name}{{x'.", exclude=player)

def handle_desc(engine, player, args: str):
    if not args:
        player.send("Usage: @desc <description>")
        return
        
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    current_room.desc = args.strip()
    engine.world.save()
    
    player.send("Room description updated.")
    current_room.broadcast(f"{{b{player.name}{{x alters the fabric of the room's atmosphere.", exclude=player)

def handle_create(engine, player, args: str):
    if not args:
        player.send("Usage: @create <item_name>")
        return
        
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    item_name = args.strip()
    new_item = Item(name=item_name, desc=f"A simple {item_name} created by a builder.")
    current_room.items.append(new_item)
    engine.world.save()
    
    player.send(f"You summon a {{g{new_item.name}{{x. (ID: {new_item.id})")
    current_room.broadcast(f"{{b{player.name}{{x summons a {{g{new_item.name}{{x out of thin air.", exclude=player)

def handle_itemdesc(engine, player, args: str):
    if not args:
        player.send("Usage: @itemdesc <item_name> <description>")
        return
        
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        player.send("Usage: @itemdesc <item_name> <description>")
        return
        
    target = parts[0].lower().strip()
    desc = parts[1].strip()
    
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    # Look for item in current room or inventory
    found_item = None
    for item in current_room.items:
        if item.name.lower() == target:
            found_item = item
            break
            
    if not found_item:
        for item in player.inventory:
            if item.name.lower() == target:
                found_item = item
                break
                
    if not found_item:
        player.send(f"You do not see '{target}' here.")
        return
        
    found_item.desc = desc
    engine.world.save()
    engine.world.save_player(player)
    
    player.send(f"Description of {{g{found_item.name}{{x set to: {desc}")

def handle_itemgettable(engine, player, args: str):
    if not args:
        player.send("Usage: @itemgettable <item_name> <true/false>")
        return
        
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        player.send("Usage: @itemgettable <item_name> <true/false>")
        return
        
    target = parts[0].lower().strip()
    val = parts[1].lower().strip()
    
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    found_item = None
    for item in current_room.items:
        if item.name.lower() == target:
            found_item = item
            break
            
    if not found_item:
        for item in player.inventory:
            if item.name.lower() == target:
                found_item = item
                break
                
    if not found_item:
        player.send(f"You do not see '{target}' here.")
        return
        
    gettable = (val == "true")
    found_item.gettable = gettable
    engine.world.save()
    engine.world.save_player(player)
    
    player.send(f"{{g{found_item.name}{{x gettable status set to: {gettable}")

def handle_spawn(engine, player, args: str):
    if not args:
        player.send("Usage: @spawn <npc_name>")
        return
        
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    npc_name = args.strip()
    new_npc = NPC(name=npc_name, desc=f"A simple {npc_name} spawned by a builder.")
    new_npc.room_id = current_room.id
    current_room.npcs.append(new_npc)
    engine.world.save()
    
    player.send(f"You spawn {{r{new_npc.name}{{x. (ID: {new_npc.id})")
    current_room.broadcast(f"{{b{player.name}{{x summons {{r{new_npc.name}{{x from the nether.", exclude=player)

def handle_npcdesc(engine, player, args: str):
    if not args:
        player.send("Usage: @npcdesc <npc_name> <description>")
        return
        
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        player.send("Usage: @npcdesc <npc_name> <description>")
        return
        
    target = parts[0].lower().strip()
    desc = parts[1].strip()
    
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    found_npc = None
    for npc in current_room.npcs:
        if npc.name.lower() == target:
            found_npc = npc
            break
            
    if not found_npc:
        player.send(f"No NPC named '{target}' found in this room.")
        return
        
    found_npc.desc = desc
    engine.world.save()
    
    player.send(f"Description of {{r{found_npc.name}{{x set to: {desc}")

def handle_npcbehavior(engine, player, args: str):
    if not args:
        player.send("Usage: @npcbehavior <npc_name> <behavior_type> <value>\nBehaviors: wander (t/f), aggressive (t/f), talk (text), shop (item:cost,item:cost)")
        return
        
    parts = args.split(maxsplit=2)
    if len(parts) < 3:
        player.send("Usage: @npcbehavior <npc_name> <behavior_type> <value>")
        return
        
    target = parts[0].lower().strip()
    behavior_type = parts[1].lower().strip()
    val = parts[2].strip()
    
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    found_npc = None
    for npc in current_room.npcs:
        if npc.name.lower() == target:
            found_npc = npc
            break
            
    if not found_npc:
        player.send(f"No NPC named '{target}' found in this room.")
        return
        
    if behavior_type in ["wander", "aggressive"]:
        found_npc.behaviors[behavior_type] = (val.lower() == "true")
    elif behavior_type == "talk":
        found_npc.behaviors["talk"] = val
    elif behavior_type == "shop":
        # Format: item:cost,item:cost
        shop_dict = {}
        items = val.split(",")
        for it in items:
            if ":" in it:
                it_parts = it.split(":")
                it_name = it_parts[0].strip()
                try:
                    it_cost = int(it_parts[1].strip())
                    shop_dict[it_name] = it_cost
                except ValueError:
                    player.send(f"{{rWarning: Ignored invalid cost '{it_parts[1]}' for '{it_name}'{{x")
        found_npc.behaviors["shop"] = shop_dict
    else:
        player.send(f"Unknown behavior type '{behavior_type}'. Use: wander, aggressive, talk, or shop.")
        return
        
    engine.world.save()
    player.send(f"{{r{found_npc.name}{{x behavior '{behavior_type}' set to: {found_npc.behaviors[behavior_type]}")

def handle_setprop(engine, player, args: str):
    if not args:
        player.send("Usage: @setprop <target> <property> <value>")
        return
        
    parts = args.split(maxsplit=2)
    if len(parts) < 3:
        player.send("Usage: @setprop <target> <property> <value>")
        return
        
    target = parts[0].lower().strip()
    prop_name = parts[1].lower().strip()
    val_str = parts[2].strip()
    val = parse_value(val_str)
    
    current_room = engine.world.rooms.get(player.room_id)
    if not current_room:
        return
        
    # Determine the target object
    tgt_obj = None
    tgt_type = ""
    
    if target == "self":
        tgt_obj = player
        tgt_type = "player"
    elif target == "room":
        tgt_obj = current_room
        tgt_type = "room"
    else:
        # Check active players
        for p in engine.players.values():
            if p.name.lower() == target:
                tgt_obj = p
                tgt_type = "player"
                break
        
        # Check room NPCs
        if not tgt_obj:
            for npc in current_room.npcs:
                if npc.name.lower() == target:
                    tgt_obj = npc
                    tgt_type = "npc"
                    break
                    
        # Check room items
        if not tgt_obj:
            for item in current_room.items:
                if item.name.lower() == target:
                    tgt_obj = item
                    tgt_type = "item"
                    break
                    
        # Check inventory items
        if not tgt_obj:
            for item in player.inventory:
                if item.name.lower() == target:
                    tgt_obj = item
                    tgt_type = "item"
                    break
                    
    if not tgt_obj:
        player.send(f"Target '{target}' not found (searched self, room, players, NPCs, items).")
        return
        
    # Set the property
    # Special properties mapping or generic properties dict
    if prop_name in ["hp", "max_hp", "gold", "admin"] and tgt_type == "player":
        tgt_obj.properties[prop_name] = val
        engine.world.save_player(tgt_obj)
    elif prop_name in ["hp", "max_hp", "damage", "gold"] and tgt_type == "npc":
        tgt_obj.properties[prop_name] = val
        engine.world.save()
    elif prop_name in ["damage"] and tgt_type == "item":
        tgt_obj.properties[prop_name] = val
        engine.world.save()
        # Item might be in player's inventory
        engine.world.save_player(player)
    else:
        # Generic property
        tgt_obj.properties[prop_name] = val
        if tgt_type == "player":
            engine.world.save_player(tgt_obj)
        else:
            engine.world.save()
            
    player.send(f"Set property '{prop_name}' on {target} ({tgt_type}) to: {val}")

def handle_rooms(engine, player, args: str):
    lines = []
    lines.append("--- Registered Rooms ---")
    for room_id, room in engine.world.rooms.items():
        lines.append(f" - {room.id}: {{C{room.name}{{x (Exits: {', '.join(room.exits.keys())})")
    player.send("\n".join(lines))

def handle_teleport(engine, player, args: str):
    if not args:
        player.send("Usage: @teleport <room_id>")
        return
        
    target_id = args.lower().strip()
    if target_id not in engine.world.rooms:
        player.send(f"Room ID '{target_id}' does not exist.")
        return
        
    current_room = engine.world.rooms.get(player.room_id)
    target_room = engine.world.rooms[target_id]
    
    # Leave current room
    if current_room:
        current_room.players.remove(player)
        current_room.broadcast(f"{{b{player.name}{{x disappears in a puff of builder smoke.", exclude=player)
        
    # Reset combat
    if player.combat_target:
        if hasattr(player.combat_target, "combat_target") and player.combat_target.combat_target == player:
            player.combat_target.combat_target = None
        player.combat_target = None
        
    # Enter target room
    player.room_id = target_room.id
    target_room.players.append(player)
    
    target_room.broadcast(f"{{b{player.name}{{x appears in a puff of builder smoke.", exclude=player)
    
    engine.world.save_player(player)
    
    # Auto-look
    from .commands import handle_look
    handle_look(engine, player, "")

# Router mapping for builder commands
BUILDER_COMMANDS = {
    "@dig": handle_dig,
    "@link": handle_link,
    "@unlink": handle_unlink,
    "@roomname": handle_roomname,
    "@desc": handle_desc,
    "@create": handle_create,
    "@itemdesc": handle_itemdesc,
    "@itemgettable": handle_itemgettable,
    "@spawn": handle_spawn,
    "@npcdesc": handle_npcdesc,
    "@npcbehavior": handle_npcbehavior,
    "@setprop": handle_setprop,
    "@rooms": handle_rooms,
    "@teleport": handle_teleport,
}
