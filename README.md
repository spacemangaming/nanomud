# Nanomud

Nanomud is a super simple, **no-coding**, builder-focused MUD (Multi-User Dungeon) engine written in Python. 

Unlike other MUD engines that require you to write Python scripts to expand the world or add objects, Nanomud lets you do **everything entirely in-game through commands** (Online Creation / OLC). The world, items, players, and NPCs are persisted automatically as human-readable JSON files.

## Features

- **No Code Required**: Start a server and construct your entire game world, items, npcs, behaviors, and stats interactively while connected.
- **Modern CLI & Packaging**: Install via `pip` and run immediately.
- **Auto-Persistence**: Any modification you make (digging a room, changing descriptions, spawning items, editing stats) is autosaved in real-time to `./nanodata/world.json`.
- **Property-Based RPG Engine**: Built-in combat, movement, vendor shops, and NPC behaviors (wandering, conversation, aggression) driven by simple object properties (e.g. `hp`, `damage`, `gold`) editable via builder commands.
- **Standard Telnet Protocol**: Connect with any client (standard telnet, PuTTY, Mudlet, etc.).
- **Zero Dependencies**: Built entirely using the Python standard library (`asyncio`).

---

## Quick Start

### 1. Installation
Install Nanomud as a package:
```bash
pip install .
```

### 2. Start the Server
Run the command in the directory where you want your database to reside:
```bash
nanomud --port 4000
```
This will automatically create a `./nanodata/` directory containing your world configuration and player profiles.

### 3. Connect to the MUD
Open a telnet client and connect to your server:
```bash
telnet localhost 4000
```
*(If you are on Windows, you can use PuTTY set to Connection Type: Telnet, Host: localhost, Port: 4000)*

The **first player to register** is automatically granted **builder admin status** and can run `@` builder commands.

---

## How to Build the World (OLC)

All builder commands start with `@`. Here is a step-by-step example of how to build a basic zone.

### 1. Digging Rooms
When you log in, you start in `The Grand Lobby` (room ID `lobby`). Let's dig a dark dungeon to the north:
```
@dig north A Dark Dungeon
```
This creates a new room called `A Dark Dungeon` (with ID `a_dark_dungeon`), links it to your north exit, and automatically creates a return exit `south` from the dungeon to the lobby.

Let's go north to inspect it:
```
north
```

### 2. Customizing Descriptions
Let's make the dungeon sound more atmospheric:
```
@desc The stone walls are covered in damp moss, and you hear water dripping in the distance.
```

### 3. Creating Items
Let's summon a weapon:
```
@create steel sword
```
Let's describe it:
```
@itemdesc steel sword A heavy sword forged from polished steel. It feels powerful in your hands.
```
By default, items can be picked up. Let's make this sword a weapon by giving it a `damage` property:
```
@setprop steel sword damage 15
```
*(When a player attacks an NPC, the engine automatically checks their inventory for items with a `damage` property and uses the highest value as their weapon damage).*

### 4. Spawning NPCs and Customizing Behaviors
Let's spawn a goblin to guard the dungeon:
```
@spawn goblin
@npcdesc goblin A small, green, sneaky goblin looking for gold.
```
Let's give the goblin some stats:
```
@setprop goblin hp 35
@setprop goblin max_hp 35
@setprop goblin damage 6
@setprop goblin gold 12
```
Now, let's configure the goblin's behavior:
- Make it wander between rooms: `@npcbehavior goblin wander true`
- Set a custom line of dialogue: `@npcbehavior goblin talk Hehehe, you won't get my gold, human!`
- Make it aggressive (attack players on sight): `@npcbehavior goblin aggressive true`

### 5. Creating Shops
You can turn any NPC into a shopkeeper. Let's create a shopkeeper back in the lobby:
```
south
@spawn merchant
@npcbehavior merchant talk Hello, traveler! Would you like to buy a potion?
@npcbehavior merchant shop potion:10,shield:50
```
This configures the merchant to sell a `potion` for 10 gold and a `shield` for 50 gold. Players can buy items from them using the `buy` command.

---

## Standard Commands Reference

### Player / Gameplay Commands
- `look` / `l` - Look around the current room.
- `look <target>` - Examine an item, NPC, or player.
- `north`, `south`, `east`, `west`, `up`, `down` (aliases: `n`, `s`, `e`, `w`, `u`, `d`) - Move in a direction.
- `say <message>` (or `"`) - Say something to everyone in the room.
- `tell <player> <message>` - Whisper a private message.
- `get <item>` / `drop <item>` - Interact with items.
- `inventory` / `i` - View your items, gold, base damage, and HP.
- `who` - See who is currently online.
- `kill <npc>` - Start round-based combat. Combats tick every 2 seconds.
- `buy <item>` - Purchase an item from a shop vendor.
- `quit` - Disconnect and save character state.
- `help` - Show command help.

### Builder Commands
- `@dig <direction> <room_name>` - Dig a new room in that direction.
- `@link <direction> <existing_room_id>` - Link exit to an existing room ID.
- `@unlink <direction>` - Remove exit in that direction.
- `@roomname <name>` - Rename the current room.
- `@desc <description>` - Set room description.
- `@create <item_name>` - Spawn an item in the room.
- `@itemdesc <item> <desc>` - Set description of an item.
- `@itemgettable <item> <t/f>` - Set if an item can be picked up.
- `@spawn <npc_name>` - Spawn a new NPC in the room.
- `@npcdesc <npc> <desc>` - Set description of an NPC.
- `@npcbehavior <npc> <behavior> <value>` - Set behaviors: `wander` (t/f), `aggressive` (t/f), `talk` (msg), `shop` (item:cost,item:cost).
- `@setprop <target> <property> <value>` - Set arbitrary properties on rooms, items, NPCs, or players (e.g. stats like `hp`, `damage`, `gold`, `admin`).
- `@rooms` - List all room IDs in the world.
- `@teleport <room_id>` - Teleport to any room by its ID.

---

## JSON Persistence Files

Nanomud stores your world in a clean, human-readable format. This makes it trivial to version control your world map using git, or manually edit stats in an editor.

- **World Map**: Saved in `nanodata/world.json`.
- **Player Accounts**: Saved in `nanodata/players/<username>.json`.
