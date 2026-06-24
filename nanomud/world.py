import os
import json
import sqlite3
import logging
from typing import Dict, List, Optional
from .models import Room, Player

logger = logging.getLogger(__name__)

class World:
    def __init__(self, data_dir: str, template: Optional[str] = None):
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "world.db")
        self.players_dir = os.path.join(data_dir, "players")
        self.rooms: Dict[str, Room] = {}
        
        self.ensure_dirs()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.load_world(template)
        
    def ensure_dirs(self):
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.players_dir, exist_ok=True)
        
    def create_tables(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error creating SQLite tables: {e}")
            
    def load_world(self, template: Optional[str] = None):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM rooms")
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("SELECT id, data FROM rooms")
                rows = cursor.fetchall()
                for row in rows:
                    room_id = row["id"]
                    room_data = json.loads(row["data"])
                    self.rooms[room_id] = Room.from_dict(room_data)
                logger.info(f"Loaded {len(self.rooms)} rooms from SQLite database at {self.db_path}")
            else:
                self.create_default_world(template)
        except Exception as e:
            logger.error(f"Error loading world: {e}")
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
        try:
            cursor = self.conn.cursor()
            for room_id, room in self.rooms.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO rooms (id, data) VALUES (?, ?)",
                    (room.id, json.dumps(room.to_dict()))
                )
            self.conn.commit()
            logger.info("Saved world to SQLite database successfully.")
        except Exception as e:
            logger.error(f"Error saving world to SQLite DB: {e}")
            try:
                self.conn.rollback()
            except Exception:
                pass
                
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

    def close(self):
        try:
            self.conn.close()
            logger.info("Closed SQLite database connection.")
        except Exception as e:
            logger.error(f"Error closing SQLite database: {e}")
