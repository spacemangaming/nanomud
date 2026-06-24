import asyncio
import hashlib
import random
import os
import logging
from typing import Dict, List, Tuple, Any, Optional
from .models import Player, Item, NPC
from .world import World
from .commands import GAME_COMMANDS, DIRECTIONS, handle_go, get_player_damage
from .builder_cmds import BUILDER_COMMANDS
from .colors import ansi_format
from .plugins import load_plugins

logger = logging.getLogger(__name__)

class Engine:
    def __init__(self, data_dir: str, start_loops: bool = True, template: Optional[str] = None, settings: Optional[Dict[str, Any]] = None):
        self.settings = settings or {}
        self.world = World(data_dir, template)
        self.players: Dict[Any, Player] = {}  # session -> Player
        self.session_states: Dict[Any, Dict[str, Any]] = {}  # session -> state dict
        self.respawn_queue: List[Tuple[float, NPC, str]] = []  # (respawn_time, NPC_instance, room_id)
        
        # Plugin registries
        self.custom_commands: Dict[str, Any] = {}
        self.event_handlers: Dict[str, List[Any]] = {}
        
        # Load plugins
        plugins_dir = os.path.join(data_dir, "plugins")
        load_plugins(self, plugins_dir)
        
        self.start_loops = start_loops
        self.combat_task = None
        self.wander_task = None
        self.respawn_task = None
        
        if start_loops:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    self.loop = asyncio.get_event_loop()
                except RuntimeError:
                    self.loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.loop)
            self.combat_task = self.loop.create_task(self.combat_tick_loop())
            self.wander_task = self.loop.create_task(self.npc_wander_tick_loop())
            self.respawn_task = self.loop.create_task(self.npc_respawn_tick_loop())

    def shutdown(self):
        """Cancel background tasks and save player state."""
        if self.start_loops:
            if self.combat_task:
                self.combat_task.cancel()
            if self.wander_task:
                self.wander_task.cancel()
            if self.respawn_task:
                self.respawn_task.cancel()
        for player in list(self.players.values()):
            self.world.save_player(player)

    def register_command(self, name: str, handler: Any):
        self.custom_commands[name.lower().strip()] = handler

    def command(self, name: str):
        def decorator(func):
            self.register_command(name, func)
            return func
        return decorator

    def on_event(self, event_name: str):
        def decorator(func):
            if event_name not in self.event_handlers:
                self.event_handlers[event_name] = []
            self.event_handlers[event_name].append(func)
            return func
        return decorator

    def trigger_event(self, event_name: str, *args, **kwargs):
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    self.loop.create_task(handler(*args, **kwargs))
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler '{handler.__name__}' for '{event_name}': {e}", exc_info=True)

    def hash_password(self, name: str, password: str) -> str:
        return hashlib.sha256(f"{name.lower()}:{password}".encode()).hexdigest()

    def handle_connect(self, session):
        self.session_states[session] = {"state": "ASK_NAME"}
        server_name = self.settings.get("SERVER_NAME", "Nanomud")
        session.send(f"{{WWelcome to {server_name}!{{x\nEnter your character name: ")
        self.trigger_event("player_connect", session)

    def handle_disconnect(self, session):
        player = self.players.get(session)
        if player:
            self.trigger_event("player_disconnect", player)
            # Leave current room
            room = self.world.rooms.get(player.room_id)
            if room:
                room.players.remove(player)
                room.broadcast(f"{{b{player.name}{{x has disconnected.")
            
            # Cancel combat
            if player.combat_target:
                if hasattr(player.combat_target, "combat_target") and player.combat_target.combat_target == player:
                    player.combat_target.combat_target = None
            
            # Save player state
            self.world.save_player(player)
            del self.players[session]
            logger.info(f"Player {player.name} disconnected.")
            
        if session in self.session_states:
            del self.session_states[session]

    def handle_input(self, session, line: str):
        line = line.strip()
        state_data = self.session_states.get(session)
        if not state_data:
            return

        state = state_data["state"]

        if state == "ASK_NAME":
            if not line:
                session.send("Name cannot be empty. Enter your character name: ")
                return
            name = line.strip().capitalize()
            if not name.isalpha() or len(name) < 2 or len(name) > 15:
                session.send("Name must be alphabetic and 2-15 characters long.\nEnter your character name: ")
                return
            
            # Check if player is already logged in
            for p in self.players.values():
                if p.name.lower() == name.lower():
                    session.send("That character is already logged in!\nEnter your character name: ")
                    return
            
            state_data["name"] = name
            if self.world.player_exists(name):
                state_data["state"] = "ASK_PASSWORD"
                session.send("Password: ", echo=False)
            else:
                state_data["state"] = "ASK_NEW_PASSWORD"
                session.send(f"Creating a new character '{name}'.\nEnter a password: ", echo=False)

        elif state == "ASK_PASSWORD":
            name = state_data["name"]
            pwd_hash = self.hash_password(name, line)
            
            player = self.world.load_player(name)
            if player and player.password_hash == pwd_hash:
                self.login_player(session, player)
            else:
                session.send("\n{rIncorrect password.{x\nEnter your character name: ", echo=True)
                state_data["state"] = "ASK_NAME"

        elif state == "ASK_NEW_PASSWORD":
            if len(line) < 4:
                session.send("\nPassword must be at least 4 characters long.\nEnter password: ", echo=False)
                return
            state_data["temp_password"] = line
            state_data["state"] = "CONFIRM_NEW_PASSWORD"
            session.send("\nConfirm password: ", echo=False)

        elif state == "CONFIRM_NEW_PASSWORD":
            if line != state_data["temp_password"]:
                session.send("\n{rPasswords do not match.{x\nEnter a password: ", echo=False)
                state_data["state"] = "ASK_NEW_PASSWORD"
                return
            
            name = state_data["name"]
            pwd_hash = self.hash_password(name, line)
            
            # Check if this is the first player (gets Admin)
            is_first_player = len(self.world.get_all_player_names()) == 0
            
            player = Player(name=name, password_hash=pwd_hash)
            if is_first_player:
                player.properties["admin"] = True
                player.send("{yYou are the first player! You have been granted builder admin status.{x\n")
            
            self.world.save_player(player)
            self.login_player(session, player)

        elif state == "PLAYING":
            player = self.players.get(session)
            if player:
                self.process_command(player, line)

    def login_player(self, session, player: Player):
        session.send("\n", echo=True)  # Turn echo back on after password prompts
        player.session = session
        self.players[session] = player
        self.session_states[session] = {"state": "PLAYING"}
        
        # Add to current room
        room = self.world.rooms.get(player.room_id)
        if not room:
            # Fallback to lobby
            player.room_id = "lobby"
            room = self.world.rooms["lobby"]
            
        room.players.append(player)
        
        # Greet room
        room.broadcast(f"{{b{player.name}{{x has entered the world.", exclude=player)
        player.send(f"{{WWelcome back, {player.name}!{{x\n")
        
        # Show look
        from .commands import handle_look
        handle_look(self, player, "")
        logger.info(f"Player {player.name} logged in.")
        self.trigger_event("player_login", player)

    def process_command(self, player: Player, line: str):
        if not line:
            return
            
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Check custom plugin-registered commands first
        if cmd in self.custom_commands:
            try:
                self.custom_commands[cmd](player, args)
            except Exception as e:
                player.send(f"{{rError executing command '{cmd}': {e}{{x")
                logger.error(f"Error in custom command '{cmd}': {e}", exc_info=True)
            return

        # Handle directions directly
        if cmd in DIRECTIONS:
            handle_go(self, player, cmd)
            return
            
        # Handle builder commands
        if cmd.startswith("@"):
            if not player.properties.get("admin", False):
                player.send("{rYou must be a builder admin to use that command.{x")
                return
            if cmd in BUILDER_COMMANDS:
                BUILDER_COMMANDS[cmd](self, player, args)
            else:
                player.send(f"Unknown builder command '{cmd}'. Type '@help' or 'help' for commands.")
            return
            
        # Handle standard gameplay commands
        if cmd in GAME_COMMANDS:
            GAME_COMMANDS[cmd](self, player, args)
            return
            
        # Check command abbreviations
        matched_cmd = None
        for k in GAME_COMMANDS.keys():
            if k.startswith(cmd):
                matched_cmd = k
                break
                
        if matched_cmd:
            GAME_COMMANDS[matched_cmd](self, player, args)
            return
            
        # Check custom exits in current room (if any exits match exactly)
        room = self.world.rooms.get(player.room_id)
        if room and cmd in room.exits:
            handle_go(self, player, cmd)
            return

        # Special commands
        if cmd == "quit":
            player.send("Safe travels! Disconnecting...")
            player.session.close()
            return
            
        player.send(f"Unknown command '{cmd}'. Type 'help' for a list of commands.")

    async def combat_tick_loop(self):
        while True:
            try:
                await asyncio.sleep(2.0)
                self.process_combat_round()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in combat tick: {e}", exc_info=True)

    def process_combat_round(self):
        # Iterate over copy of online players to avoid mutations
        for player in list(self.players.values()):
            if not player.combat_target:
                continue
                
            npc = player.combat_target
            room = self.world.rooms.get(player.room_id)
            
            # Verify they are in the same room
            if not room or npc not in room.npcs:
                player.send(f"Your target is no longer here. Combat ended.")
                player.combat_target = None
                continue
                
            # 1. Player attacks NPC
            self.trigger_event("combat_round", player, npc)
            player_dmg = get_player_damage(player)
            npc_hp = npc.properties.get("hp", 0)
            npc_max_hp = npc.properties.get("max_hp", 20)
            
            new_npc_hp = max(0, npc_hp - player_dmg)
            npc.properties["hp"] = new_npc_hp
            
            player.send(f"You hit {{r{npc.name}{{x for {player_dmg} damage! ({new_npc_hp}/{npc_max_hp} HP)")
            room.broadcast(f"{{b{player.name}{{x hits {{r{npc.name}{{x for {player_dmg} damage!", exclude=player)
            
            if new_npc_hp <= 0:
                # NPC Dies!
                player.send(f"{{RYou have slain {npc.name}!{{x")
                room.broadcast(f"{{b{player.name}{{x has slain {{r{npc.name}{{x!", exclude=player)
                
                # Reward gold
                gold_reward = npc.properties.get("gold", 0)
                if gold_reward > 0:
                    player.properties["gold"] = player.properties.get("gold", 0) + gold_reward
                    player.send(f"You receive {gold_reward} gold!")
                    
                # Trigger event before removing NPC
                self.trigger_event("npc_death", player, npc)
                
                # Stop combat
                player.combat_target = None
                
                # Remove NPC from room and queue respawn
                room.npcs.remove(npc)
                respawn_delay = 30.0  # seconds
                respawn_time = self.loop.time() + respawn_delay
                self.respawn_queue.append((respawn_time, npc, room.id))
                
                # Save world and player
                self.world.save()
                self.world.save_player(player)
                continue
                
            # 2. NPC attacks Player (if still alive)
            npc_dmg = npc.properties.get("damage", 2)
            player_hp = player.properties.get("hp", 100)
            player_max_hp = player.properties.get("max_hp", 100)
            
            new_player_hp = max(0, player_hp - npc_dmg)
            player.properties["hp"] = new_player_hp
            
            player.send(f"{{r{npc.name}{{x hits you for {npc_dmg} damage! ({new_player_hp}/{player_max_hp} HP)")
            room.broadcast(f"{{r{npc.name}{{x hits {{b{player.name}{{x for {npc_dmg} damage!", exclude=player)
            
            if new_player_hp <= 0:
                # Player Dies!
                player.send("{rYou have been slain!{x")
                room.broadcast(f"{{b{player.name}{{x has been slain by {{r{npc.name}{{x!", exclude=player)
                
                self.trigger_event("player_death", player, npc)
                
                # Reset player and teleport to lobby
                player.properties["hp"] = player_max_hp
                player.combat_target = None
                
                room.players.remove(player)
                
                lobby = self.world.rooms.get("lobby")
                if lobby:
                    player.room_id = "lobby"
                    lobby.players.append(player)
                    lobby.broadcast(f"{{b{player.name}{{x appears in a flash of resurrection light.", exclude=player)
                    player.send("You resurrect in the lobby.")
                    from .commands import handle_look
                    handle_look(self, player, "")
                
                self.world.save_player(player)

    async def npc_wander_tick_loop(self):
        while True:
            try:
                await asyncio.sleep(10.0)
                self.process_npc_wander()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in NPC wander: {e}")

    def process_npc_wander(self):
        for room_id, room in list(self.world.rooms.items()):
            # Copy NPCs list because we might mutate it by moving NPCs
            for npc in list(room.npcs):
                if npc.behaviors.get("wander") and not npc.combat_target:
                    # 20% chance to wander
                    if random.random() < 0.20 and room.exits:
                        direction = random.choice(list(room.exits.keys()))
                        target_room_id = room.exits[direction]
                        target_room = self.world.rooms.get(target_room_id)
                        
                        if target_room:
                            room.npcs.remove(npc)
                            room.broadcast(f"{{r{npc.name}{{x wanders off to the {direction}.")
                            
                            npc.room_id = target_room.id
                            target_room.npcs.append(npc)
                            
                            opposites = {
                                "north": "the south", "south": "the north",
                                "east": "the west", "west": "the east",
                                "up": "below", "down": "above"
                            }
                            from_dir = opposites.get(direction, "somewhere")
                            target_room.broadcast(f"{{r{npc.name}{{x wanders in from {from_dir}.")
                            
                            # Aggressive NPC checks for players in the target room
                            if npc.behaviors.get("aggressive") and target_room.players:
                                target_player = random.choice(target_room.players)
                                npc.combat_target = target_player
                                target_player.combat_target = npc
                                target_room.broadcast(f"{{r{npc.name}{{x growls and attacks {{b{target_player.name}{{x!")
                                
        # Save world if any NPC positions updated
        self.world.save()

    async def npc_respawn_tick_loop(self):
        while True:
            try:
                await asyncio.sleep(2.0)
                current_time = self.loop.time()
                
                # Process respawns
                ready_respawns = []
                remaining_respawns = []
                for respawn in self.respawn_queue:
                    respawn_time, npc, room_id = respawn
                    if current_time >= respawn_time:
                        ready_respawns.append((npc, room_id))
                    else:
                        remaining_respawns.append(respawn)
                        
                self.respawn_queue = remaining_respawns
                
                for npc, room_id in ready_respawns:
                    room = self.world.rooms.get(room_id)
                    if room:
                        # Reset NPC health
                        npc.properties["hp"] = npc.properties.get("max_hp", 20)
                        npc.room_id = room.id
                        room.npcs.append(npc)
                        room.broadcast(f"{{r{npc.name}{{x has respawned.")
                        
                        # Aggressive check
                        if npc.behaviors.get("aggressive") and room.players:
                            target_player = random.choice(room.players)
                            npc.combat_target = target_player
                            target_player.combat_target = npc
                            room.broadcast(f"{{r{npc.name}{{x growls and attacks {{b{target_player.name}{{x!")
                            
                if ready_respawns:
                    self.world.save()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in NPC respawn loop: {e}")
