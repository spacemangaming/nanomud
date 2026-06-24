from typing import Any, List
from .colors import ansi_format

def get_player_damage(player) -> int:
    """Find the highest damage weapon in player's inventory or return base damage (2)."""
    max_dmg = 2
    for item in player.inventory:
        dmg = item.properties.get("damage")
        if dmg is not None:
            try:
                max_dmg = max(max_dmg, int(dmg))
            except (ValueError, TypeError):
                pass
    return max_dmg

def handle_look(engine, player, args: str):
    room = engine.world.rooms.get(player.room_id)
    if not room:
        player.send("{rYou are in the void. There is nothing to look at.{x")
        return

    if not args:
        # Look at the room
        lines = []
        lines.append(f"{{C{room.name}{{x (ID: {room.id})")
        lines.append(room.desc)
        
        # Exits
        exits_str = ", ".join(room.exits.keys()) if room.exits else "none"
        lines.append(f"{{yExits:{{x {exits_str}")
        
        # Items
        items_in_room = [f"{{g{i.name}{{x" for i in room.items]
        if items_in_room:
            lines.append(f"You see: {', '.join(items_in_room)}")
            
        # NPCs
        npcs_in_room = [f"{{r{n.name}{{x" for n in room.npcs]
        if npcs_in_room:
            lines.append(f"NPCs: {', '.join(npcs_in_room)}")
            
        # Other Players
        other_players = [f"{{b{p.name}{{x" for p in room.players if p != player]
        if other_players:
            lines.append(f"Players: {', '.join(other_players)}")
            
        player.send("\n".join(lines))
    else:
        # Look at a specific target (item, NPC, or player)
        target = args.lower().strip()
        
        # Check room NPCs
        for npc in room.npcs:
            if npc.name.lower() == target:
                hp_str = f"HP: {npc.properties.get('hp')}/{npc.properties.get('max_hp')}" if 'hp' in npc.properties else ""
                player.send(f"{{r{npc.name}{{x: {npc.desc} {hp_str}")
                return
                
        # Check room items
        for item in room.items:
            if item.name.lower() == target:
                player.send(f"{{g{item.name}{{x: {item.desc}")
                return
                
        # Check inventory items
        for item in player.inventory:
            if item.name.lower() == target:
                player.send(f"{{g{item.name}{{x (inventory): {item.desc}")
                return
                
        # Check other players in the room
        for p in room.players:
            if p.name.lower() == target:
                hp_str = f"HP: {p.properties.get('hp')}/{p.properties.get('max_hp')}"
                player.send(f"{{b{p.name}{{x: A fellow adventurer. {hp_str}")
                return
                
        player.send(f"You do not see '{args}' here.")

def handle_go(engine, player, direction: str):
    room = engine.world.rooms.get(player.room_id)
    if not room:
        player.send("{rYou are trapped in the void!{x")
        return
        
    direction = direction.lower().strip()
    # Aliases
    aliases = {
        "n": "north", "s": "south", "e": "east", "w": "west",
        "u": "up", "d": "down"
    }
    direction = aliases.get(direction, direction)
    
    if direction not in room.exits:
        player.send(f"You cannot go {direction}.")
        return
        
    target_id = room.exits[direction]
    target_room = engine.world.rooms.get(target_id)
    if not target_room:
        player.send(f"{{rThe exit leads to nowhere (invalid room ID: {target_id}).{{x")
        return
        
    # Cancel combat on move
    if player.combat_target:
        player.send("{yYou flee from combat!{x")
        if hasattr(player.combat_target, "combat_target") and player.combat_target.combat_target == player:
            player.combat_target.combat_target = None
        player.combat_target = None
        
    # Leave current room
    room.players.remove(player)
    room.broadcast(f"{{b{player.name}{{x leaves {direction}.", exclude=player)
    
    # Enter new room
    player.room_id = target_room.id
    target_room.players.append(player)
    
    # Notify room
    # Opposite direction for entrance message
    opposites = {
        "north": "the south", "south": "the north",
        "east": "the west", "west": "the east",
        "up": "below", "down": "above"
    }
    from_dir = opposites.get(direction, "somewhere")
    target_room.broadcast(f"{{b{player.name}{{x arrives from {from_dir}.", exclude=player)
    
    # Auto-look
    handle_look(engine, player, "")
    
    # Save player's new location
    engine.world.save_player(player)

def handle_say(engine, player, args: str):
    if not args:
        player.send("Say what?")
        return
    room = engine.world.rooms.get(player.room_id)
    if room:
        room.broadcast(f"{{b{player.name}{{x says, \"{args}\"")

def handle_tell(engine, player, args: str):
    if not args:
        player.send("Tell who what?")
        return
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        player.send(f"What do you want to tell {parts[0]}?")
        return
    
    target_name = parts[0].lower()
    msg = parts[1]
    
    target_player = None
    for p in engine.players.values():
        if p.name.lower() == target_name:
            target_player = p
            break
            
    if not target_player:
        player.send(f"Player '{parts[0]}' is not online.")
        return
        
    target_player.send(f"{{b{player.name}{{x whispers to you: {msg}")
    player.send(f"You whisper to {{b{target_player.name}{{x: {msg}")

def handle_get(engine, player, args: str):
    if not args:
        player.send("Get what?")
        return
    
    room = engine.world.rooms.get(player.room_id)
    if not room:
        return
        
    target = args.lower().strip()
    found_item = None
    for item in room.items:
        if item.name.lower() == target:
            found_item = item
            break
            
    if not found_item:
        player.send(f"You do not see '{args}' here.")
        return
        
    if not found_item.gettable:
        player.send("You cannot pick that up.")
        return
        
    room.items.remove(found_item)
    player.inventory.append(found_item)
    
    player.send(f"You pick up the {{g{found_item.name}{{x.")
    room.broadcast(f"{{b{player.name}{{x picks up a {{g{found_item.name}{{x.", exclude=player)
    
    # Save world and player
    engine.world.save()
    engine.world.save_player(player)

def handle_drop(engine, player, args: str):
    if not args:
        player.send("Drop what?")
        return
        
    room = engine.world.rooms.get(player.room_id)
    if not room:
        return
        
    target = args.lower().strip()
    found_item = None
    for item in player.inventory:
        if item.name.lower() == target:
            found_item = item
            break
            
    if not found_item:
        player.send("You are not carrying that.")
        return
        
    player.inventory.remove(found_item)
    room.items.append(found_item)
    
    player.send(f"You drop the {{g{found_item.name}{{x.")
    room.broadcast(f"{{b{player.name}{{x drops a {{g{found_item.name}{{x.", exclude=player)
    
    # Save world and player
    engine.world.save()
    engine.world.save_player(player)

def handle_inventory(engine, player, args: str):
    lines = []
    lines.append(f"--- {{CCharacter Info: {player.name}{{x ---")
    lines.append(f"HP: {player.properties.get('hp', 100)}/{player.properties.get('max_hp', 100)}")
    lines.append(f"Gold: {player.properties.get('gold', 0)}")
    dmg = get_player_damage(player)
    lines.append(f"Base Damage: {dmg}")
    lines.append(f"Admin Status: {'Yes' if player.properties.get('admin', False) else 'No'}")
    
    lines.append("\n--- Inventory ---")
    if not player.inventory:
        lines.append("Empty.")
    else:
        for item in player.inventory:
            lines.append(f" - {{g{item.name}{{x: {item.desc}")
            
    player.send("\n".join(lines))

def handle_who(engine, player, args: str):
    lines = []
    lines.append("--- Online Players ---")
    for p in engine.players.values():
        room_name = "The Void"
        room = engine.world.rooms.get(p.room_id)
        if room:
            room_name = room.name
        lines.append(f" - {{b{p.name}{{x currently in {room_name}")
    player.send("\n".join(lines))

def handle_kill(engine, player, args: str):
    if not args:
        player.send("Attack what?")
        return
        
    room = engine.world.rooms.get(player.room_id)
    if not room:
        return
        
    target = args.lower().strip()
    found_npc = None
    for npc in room.npcs:
        if npc.name.lower() == target:
            found_npc = npc
            break
            
    if not found_npc:
        player.send(f"You do not see a '{args}' here.")
        return
        
    if 'hp' not in found_npc.properties:
        player.send("You cannot attack that.")
        return
        
    player.combat_target = found_npc
    found_npc.combat_target = player
    
    player.send(f"You attack {{r{found_npc.name}{{x! (Combat started)")
    room.broadcast(f"{{b{player.name}{{x attacks {{r{found_npc.name}{{x!", exclude=player)

def handle_buy(engine, player, args: str):
    if not args:
        player.send("Buy what?")
        return
        
    room = engine.world.rooms.get(player.room_id)
    if not room:
        return
        
    # Check if there is an NPC with shop behavior in the room
    shopkeeper = None
    shop_items = {}
    for npc in room.npcs:
        if "shop" in npc.behaviors and isinstance(npc.behaviors["shop"], dict):
            shopkeeper = npc
            shop_items = npc.behaviors["shop"]
            break
            
    if not shopkeeper:
        player.send("There is no shopkeeper here.")
        return
        
    target_item_name = args.lower().strip()
    # Matches case-insensitive key in shop dict
    matched_name = None
    price = None
    for item_name, cost in shop_items.items():
        if item_name.lower() == target_item_name:
            matched_name = item_name
            price = cost
            break
            
    if not matched_name:
        player.send(f"{shopkeeper.name} does not sell '{args}'.")
        return
        
    try:
        price = int(price)
    except (ValueError, TypeError):
        player.send(f"{{rError: Invalid shop price configured for {matched_name}.{{x")
        return
        
    player_gold = player.properties.get("gold", 0)
    if player_gold < price:
        player.send(f"You cannot afford that. It costs {price} gold, but you only have {player_gold}.")
        return
        
    # Create the item
    from .models import Item
    new_item = Item(name=matched_name, desc=f"A standard {matched_name} bought from a shop.", gettable=True)
    
    player.properties["gold"] = player_gold - price
    player.inventory.append(new_item)
    
    player.send(f"You buy a {{g{new_item.name}{{x from {shopkeeper.name} for {price} gold.")
    room.broadcast(f"{{b{player.name}{{x buys a {{g{new_item.name}{{x from {shopkeeper.name}.", exclude=player)
    
    engine.world.save_player(player)

def handle_help(engine, player, args: str):
    lines = []
    lines.append("--- {{CNanomud Gameplay Commands{{x ---")
    lines.append("  {{ylook{{x / {{yl{{x                - Look around the current room")
    lines.append("  {{ylook <target>{{x          - Examine an item, NPC, or player")
    lines.append("  {{ynorth{{x, {{ysouth{{x, etc.      - Move in a direction (aliases: n, s, e, w, u, d)")
    lines.append("  {{ysay <message>{{x / {{y\"{{x       - Speak to the room")
    lines.append("  {{ytell <player> <msg>{{x    - Send a private message to a player")
    lines.append("  {{yget <item>{{x             - Pick up an item from the room")
    lines.append("  {{ydrop <item>{{x            - Drop an item from inventory")
    lines.append("  {{yinventory{{x / {{yi{{x          - View your items, gold, and stats")
    lines.append("  {{ywho{{x                    - See who is currently online")
    lines.append("  {{ykill <npc>{{x             - Initiate combat with an NPC")
    lines.append("  {{ybuy <item>{{x             - Buy an item from a shop vendor NPC")
    lines.append("  {{yquit{{x                   - Save and disconnect")
    
    if player.properties.get("admin", False):
        lines.append("\n--- {{CBuilder Commands (OLC){{x ---")
        lines.append("  {{y@dig <dir> <room_name>{{x - Dig a new room in that direction")
        lines.append("  {{y@link <dir> <room_id>{{x  - Link current room exit to existing room")
        lines.append("  {{y@unlink <dir>{{x          - Remove an exit in that direction")
        lines.append("  {{y@roomname <new_name>{{x   - Rename current room")
        lines.append("  {{y@desc <description>{{x    - Set current room description")
        lines.append("  {{y@create <item_name>{{x    - Create an item in the room")
        lines.append("  {{y@itemdesc <item> <desc>{{x- Set description of an item in the room")
        lines.append("  {{y@itemgettable <item> <t/f>{{x - Set if item can be picked up")
        lines.append("  {{y@spawn <npc_name>{{x      - Spawn a new NPC in the room")
        lines.append("  {{y@npcdesc <npc> <desc>{{x  - Set description of NPC")
        lines.append("  {{y@npcbehavior <npc> <bhv> <val>{{x - Set behavior (wander, aggressive, talk, shop)")
        lines.append("  {{y@setprop <tgt> <prop> <val>{{x - Set stats (e.g. self/sword/goblin hp/damage/gold)")
        lines.append("  {{y@rooms{{x                  - List all room IDs in the world")
        lines.append("  {{y@teleport <room_id>{{x    - Teleport to any room ID")
        
    player.send("\n".join(lines))

# Command Router mapping names to functions
GAME_COMMANDS = {
    "look": handle_look,
    "l": handle_look,
    "say": handle_say,
    "tell": handle_tell,
    "whisper": handle_tell,
    "get": handle_get,
    "take": handle_get,
    "drop": handle_drop,
    "inventory": handle_inventory,
    "i": handle_inventory,
    "who": handle_who,
    "kill": handle_kill,
    "buy": handle_buy,
    "help": handle_help,
}

DIRECTIONS = ["north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"]
