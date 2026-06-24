import uuid
from typing import Dict, List, Any, Optional

class Item:
    def __init__(self, name: str, desc: str = "A simple item.", gettable: bool = True, item_id: Optional[str] = None):
        self.id = item_id or f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        self.name = name
        self.desc = desc
        self.gettable = gettable
        self.properties: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "gettable": self.gettable,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        item = cls(
            name=data["name"],
            desc=data.get("desc", "A simple item."),
            gettable=data.get("gettable", True),
            item_id=data.get("id")
        )
        item.properties = data.get("properties", {})
        return item


class NPC:
    def __init__(self, name: str, desc: str = "A mysterious figure.", npc_id: Optional[str] = None):
        self.id = npc_id or f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        self.name = name
        self.desc = desc
        self.behaviors: Dict[str, Any] = {}
        self.properties: Dict[str, Any] = {
            "hp": 20,
            "max_hp": 20,
            "damage": 5,
            "gold": 5
        }
        self.room_id: Optional[str] = None
        self.combat_target: Any = None  # In-memory reference to active combat target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "behaviors": self.behaviors,
            "properties": self.properties,
            "room_id": self.room_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NPC":
        npc = cls(
            name=data["name"],
            desc=data.get("desc", "A mysterious figure."),
            npc_id=data.get("id")
        )
        npc.behaviors = data.get("behaviors", {})
        # Update default properties with loaded properties
        npc.properties.update(data.get("properties", {}))
        npc.room_id = data.get("room_id")
        return npc


class Room:
    def __init__(self, room_id: str, name: str, desc: str = "An empty room."):
        self.id = room_id.lower().replace(" ", "_")
        self.name = name
        self.desc = desc
        self.exits: Dict[str, str] = {}  # direction -> target_room_id
        self.items: List[Item] = []
        self.npcs: List[NPC] = []
        self.properties: Dict[str, Any] = {}
        self.players: List[Any] = []  # In-memory list of active Player objects

    def broadcast(self, message: str, exclude: Optional[Any] = None):
        """Send a message to all players in this room."""
        for player in self.players:
            if player != exclude:
                player.send(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "desc": self.desc,
            "exits": self.exits,
            "items": [item.to_dict() for item in self.items],
            "npcs": [npc.to_dict() for npc in self.npcs],
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Room":
        room = cls(
            room_id=data["id"],
            name=data["name"],
            desc=data.get("desc", "An empty room.")
        )
        room.exits = data.get("exits", {})
        room.items = [Item.from_dict(i) for i in data.get("items", [])]
        room.npcs = [NPC.from_dict(n) for n in data.get("npcs", [])]
        for npc in room.npcs:
            npc.room_id = room.id
        room.properties = data.get("properties", {})
        return room


class Player:
    def __init__(self, name: str, password_hash: str):
        self.name = name
        self.password_hash = password_hash
        self.room_id: str = "lobby"
        self.inventory: List[Item] = []
        self.properties: Dict[str, Any] = {
            "hp": 100,
            "max_hp": 100,
            "gold": 0,
            "admin": False
        }
        self.session: Optional[Any] = None  # In-memory telnet session
        self.combat_target: Optional[Any] = None  # In-memory NPC or Player target

    def send(self, text: str):
        """Send colored message to this player."""
        if self.session:
            self.session.send(text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "password_hash": self.password_hash,
            "room_id": self.room_id,
            "inventory": [item.to_dict() for item in self.inventory],
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        player = cls(
            name=data["name"],
            password_hash=data["password_hash"]
        )
        player.room_id = data.get("room_id", "lobby")
        player.inventory = [Item.from_dict(i) for i in data.get("inventory", [])]
        # Update default properties with loaded properties
        player.properties.update(data.get("properties", {}))
        return player
