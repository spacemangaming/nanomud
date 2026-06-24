import unittest
import tempfile
import shutil
import os
from nanomud.colors import ansi_format, strip_colors
from nanomud.models import Room, Item, NPC, Player
from nanomud.world import World
from nanomud.engine import Engine

class TestColors(unittest.TestCase):
    def test_color_format(self):
        self.assertEqual(ansi_format("{rRed{x"), "\033[31mRed\033[0m")
        self.assertEqual(ansi_format("{RBoldRed{x"), "\033[1;31mBoldRed\033[0m")
        self.assertEqual(strip_colors("{rRed{x"), "Red")


class TestModels(unittest.TestCase):
    def test_item_serialization(self):
        item = Item("iron sword", "A heavy sword.", gettable=True)
        item.properties["damage"] = 15
        
        data = item.to_dict()
        loaded = Item.from_dict(data)
        
        self.assertEqual(loaded.name, "iron sword")
        self.assertEqual(loaded.desc, "A heavy sword.")
        self.assertTrue(loaded.gettable)
        self.assertEqual(loaded.properties["damage"], 15)

    def test_npc_serialization(self):
        npc = NPC("goblin", "A green goblin.")
        npc.behaviors["wander"] = True
        npc.properties["hp"] = 35
        
        data = npc.to_dict()
        loaded = NPC.from_dict(data)
        
        self.assertEqual(loaded.name, "goblin")
        self.assertTrue(loaded.behaviors["wander"])
        self.assertEqual(loaded.properties["hp"], 35)

    def test_room_serialization(self):
        room = Room("hallway", "Damp Hallway", "A damp stone hallway.")
        room.exits["north"] = "lobby"
        
        item = Item("key", "A shiny key.")
        room.items.append(item)
        
        npc = NPC("rat", "A giant rat.")
        room.npcs.append(npc)
        
        data = room.to_dict()
        loaded = Room.from_dict(data)
        
        self.assertEqual(loaded.id, "hallway")
        self.assertEqual(loaded.name, "Damp Hallway")
        self.assertEqual(loaded.exits["north"], "lobby")
        self.assertEqual(len(loaded.items), 1)
        self.assertEqual(loaded.items[0].name, "key")
        self.assertEqual(len(loaded.npcs), 1)
        self.assertEqual(loaded.npcs[0].name, "rat")


class TestEngineAndWorld(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = Engine(self.temp_dir, start_loops=False)
        
    def tearDown(self):
        self.engine.shutdown()
        shutil.rmtree(self.temp_dir)

    def test_world_init(self):
        # Default world should have lobby
        self.assertIn("lobby", self.engine.world.rooms)
        lobby = self.engine.world.rooms["lobby"]
        self.assertEqual(lobby.name, "The Grand Lobby")

    def test_player_create_and_load(self):
        password = "secretpassword"
        name = "Tester"
        pwd_hash = self.engine.hash_password(name, password)
        
        player = Player(name=name, password_hash=pwd_hash)
        player.properties["gold"] = 100
        
        self.engine.world.save_player(player)
        
        # Verify exists
        self.assertTrue(self.engine.world.player_exists(name))
        
        # Load and check properties
        loaded = self.engine.world.load_player(name)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, name)
        self.assertEqual(loaded.password_hash, pwd_hash)
        self.assertEqual(loaded.properties["gold"], 100)

    def test_builder_dig_and_setprop(self):
        # Create a mock player with admin access
        admin_player = Player(name="Admin", password_hash="hash")
        admin_player.properties["admin"] = True
        admin_player.room_id = "lobby"
        
        # Register player to lobby
        lobby = self.engine.world.rooms["lobby"]
        lobby.players.append(admin_player)
        
        # Mock session to capture output
        class MockSession:
            def __init__(self):
                self.output = []
            def send(self, text, echo=None):
                self.output.append(text)
        
        session = MockSession()
        admin_player.session = session
        self.engine.players[session] = admin_player
        
        # 1. Test @dig command
        self.engine.process_command(admin_player, "@dig north The Dark Vault")
        
        # Verify room was created
        self.assertIn("the_dark_vault", self.engine.world.rooms)
        vault = self.engine.world.rooms["the_dark_vault"]
        self.assertEqual(vault.name, "The Dark Vault")
        self.assertEqual(lobby.exits["north"], "the_dark_vault")
        self.assertEqual(vault.exits["south"], "lobby")
        
        # 2. Test @create command
        self.engine.process_command(admin_player, "@create shield")
        self.assertEqual(len(lobby.items), 1)
        self.assertEqual(lobby.items[0].name, "shield")
        
        # 3. Test @setprop command
        shield_name = lobby.items[0].name
        self.engine.process_command(admin_player, f"@setprop shield armor 10")
        self.assertEqual(lobby.items[0].properties["armor"], 10)

    def test_template_loading(self):
        # Create a new engine with fantasy template
        temp_dir_2 = tempfile.mkdtemp()
        try:
            engine_fantasy = Engine(temp_dir_2, start_loops=False, template="fantasy")
            # Should have loaded rooms: tavern, dark_forest, goblin_cave
            self.assertIn("tavern", engine_fantasy.world.rooms)
            self.assertIn("dark_forest", engine_fantasy.world.rooms)
            self.assertIn("goblin_cave", engine_fantasy.world.rooms)
            
            tavern = engine_fantasy.world.rooms["tavern"]
            self.assertEqual(tavern.name, "The Rusty Dagger Tavern")
            
            # Check merchant NPC exists in tavern
            self.assertEqual(len(tavern.npcs), 1)
            self.assertEqual(tavern.npcs[0].name, "merchant")
        finally:
            shutil.rmtree(temp_dir_2)

if __name__ == "__main__":
    unittest.main()
