import os
import json
import logging
from typing import Dict, List, Optional
from .models import Room, Player

logger = logging.getLogger(__name__)

class World:
    def __init__(self, data_dir: str, template: Optional[str] = None):
        self.data_dir = data_dir
        self.world_file = os.path.join(data_dir, "world.json")
        self.players_dir = os.path.join(data_dir, "players")
        self.rooms: Dict[str, Room] = {}
        
        self.ensure_dirs()
        self.load_world(template)
        
    def ensure_dirs(self):
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.players_dir, exist_ok=True)
        
    def load_world(self, template: Optional[str] = None):
        if os.path.exists(self.world_file):
            try:
                with open(self.world_file, "r") as f:
                    data = json.load(f)
                for room_id, room_data in data.get("rooms", {}).items():
                    self.rooms[room_id] = Room.from_dict(room_data)
                logger.info(f"Loaded {len(self.rooms)} rooms from {self.world_file}")
            except Exception as e:
                logger.error(f"Error loading world: {e}")
                self.create_default_world(template)
        else:
            self.create_default_world(template)
            
    def create_default_world(self, template: Optional[str] = None):
        if template:
            package_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(package_dir, "templates", f"{template}.json")
            if os.path.exists(template_path):
                try:
                    with open(template_path, "r") as f:
                        data = json.load(f)
                    for room_id, room_data in data.get("rooms", {}).items():
                        self.rooms[room_id] = Room.from_dict(room_data)
                    logger.info(f"Initialized world from template '{template}'")
                    self.save()
                    return
                except Exception as e:
                    logger.error(f"Error loading template '{template}': {e}")
            else:
                logger.error(f"Template '{template}' not found at {template_path}. Falling back to default.")

        lobby = Room(
            room_id="lobby",
            name="The Grand Lobby",
            desc="Welcome to your new MUD! This is the starting room. Use {y@help{x to see builder commands."
        )
        self.rooms["lobby"] = lobby
        self.save()
        
    def save(self):
        temp_file = self.world_file + ".tmp"
        try:
            data = {
                "rooms": {room_id: room.to_dict() for room_id, room in self.rooms.items()}
            }
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, self.world_file)
        except Exception as e:
            logger.error(f"Error saving world: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    def player_exists(self, name: str) -> bool:
        filename = os.path.join(self.players_dir, f"{name.lower()}.json")
        return os.path.exists(filename)
        
    def load_player(self, name: str) -> Optional[Player]:
        filename = os.path.join(self.players_dir, f"{name.lower()}.json")
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            return Player.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading player {name}: {e}")
            return None
            
    def save_player(self, player: Player):
        filename = os.path.join(self.players_dir, f"{player.name.lower()}.json")
        temp_file = filename + ".tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(player.to_dict(), f, indent=2)
            os.replace(temp_file, filename)
        except Exception as e:
            logger.error(f"Error saving player {player.name}: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    def get_all_player_names(self) -> List[str]:
        names = []
        try:
            for file in os.listdir(self.players_dir):
                if file.endswith(".json"):
                    names.append(file[:-5])
        except Exception:
            pass
        return names
