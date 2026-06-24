import argparse
from .server import TelnetServer

def print_guide():
    guide_text = """
========================================
       NANOMUD COMMAND REFERENCE        
========================================

Gameplay Commands:
-----------------
  look / l                - Examine the current room (exits, items, NPCs, players).
  look <target>           - Look at a specific item, NPC, or player.
  north / south / east / west / up / down (or n/s/e/w/u/d)
                          - Move in that direction.
  say <message> (or ")    - Chat with everyone in the current room.
  tell <player> <msg>     - Send a private message to a player.
  get <item>              - Pick up an item from the floor.
  drop <item>             - Drop an item from your inventory.
  inventory / i           - View your current stats (HP, gold, damage) and carried items.
  who                     - List all players currently online.
  kill <npc>              - Attack an NPC (starts automatic round-based combat).
  buy <item>              - Purchase an item from a shop vendor.
  help                    - Show help commands inside the game.
  quit                    - Disconnect and save character.

Builder (OLC) Commands (Admins only):
------------------------------------
  @dig <dir> <room name>  - Create a new room in that direction and link it.
  @link <dir> <room_id>   - Link exit to an existing room by its ID.
  @unlink <dir>           - Remove an exit.
  @roomname <name>        - Rename the current room.
  @desc <description>     - Set the description of the current room.
  @create <item name>     - Spawn a new item in the room.
  @itemdesc <item> <desc> - Set the description of an item in the room/inventory.
  @itemgettable <item> <t/f> - Set if an item can be picked up (true or false).
  @spawn <npc name>       - Spawn a new NPC in the room.
  @npcdesc <npc> <desc>   - Set the description of an NPC.
  @npcbehavior <npc> <behavior> <value>
                          - Configure behaviors: wander (t/f), aggressive (t/f),
                            talk (msg), or shop (item:cost,item:cost).
  @setprop <tgt> <prop> <val>
                          - Set stats/properties (e.g. self hp 100, sword damage 15).
  @rooms                  - List all room IDs in the world database.
  @teleport <room_id>     - Teleport to any room by its ID.
========================================
"""
    print(guide_text)

def main():
    parser = argparse.ArgumentParser(description="Nanomud: A super simple no-coding builder MUD engine.")
    parser.add_argument("--host", default=None, help="Host address to bind to (overrides serversettings.py)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (overrides serversettings.py)")
    parser.add_argument("--data", default="./nanodata", help="Directory for world and player JSON files (default: ./nanodata)")
    parser.add_argument("--template", choices=["fantasy", "modern", "scifi"], default=None, help="Initialize the world with a theme template if no database exists")
    parser.add_argument("--guide", action="store_true", help="Print the in-game command reference guide and exit")
    
    args = parser.parse_args()
    
    if args.guide:
        print_guide()
        return
        
    # Load server settings (creates default if not found)
    from .settings import load_settings
    settings = load_settings(args.data)
    
    # Resolve parameters: CLI overrides serversettings.py, which overrides hardcoded defaults
    host = args.host if args.host is not None else settings.get("HOST", "0.0.0.0")
    port = args.port if args.port is not None else settings.get("PORT", 4000)
    template = args.template if args.template is not None else settings.get("TEMPLATE", None)
    
    server = TelnetServer(host=host, port=port, data_dir=args.data, template=template, settings=settings)
    server.run()

if __name__ == "__main__":
    main()
