import os
import sys
import importlib.util
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: Dict[str, Any] = {
    "HOST": "0.0.0.0",
    "PORT": 4000,
    "SERVER_NAME": "Nanomud",
    "TEMPLATE": None,
}

DEFAULT_SETTINGS_FILE_CONTENT = """# Nanomud Server Settings Configuration

# The network address the server will bind to. Use "0.0.0.0" to listen on all interfaces.
HOST = "0.0.0.0"

# The port number the server will listen on.
PORT = 4000

# The name of your MUD game.
SERVER_NAME = "Nanomud"

# The template to initialize the world database with if it doesn't exist.
# Choose from: None, "fantasy", "modern", "scifi"
TEMPLATE = None
"""

def load_settings(data_dir: str) -> Dict[str, Any]:
    """
    Check CWD and data_dir for serversettings.py.
    If not found, write a default file to data_dir/serversettings.py.
    Load settings and return as a dict.
    """
    settings = DEFAULT_SETTINGS.copy()
    
    # Paths to check
    cwd_file = os.path.abspath("serversettings.py")
    data_file = os.path.abspath(os.path.join(data_dir, "serversettings.py"))
    
    settings_file = None
    if os.path.exists(cwd_file):
        settings_file = cwd_file
    elif os.path.exists(data_file):
        settings_file = data_file
    else:
        # Create default in data directory
        try:
            os.makedirs(data_dir, exist_ok=True)
            with open(data_file, "w") as f:
                f.write(DEFAULT_SETTINGS_FILE_CONTENT)
            settings_file = data_file
            logger.info(f"Created default server settings at {data_file}")
            print(f"Created default server settings at {data_file}")
        except Exception as e:
            logger.error(f"Failed to create default server settings: {e}")
            
    if settings_file and os.path.exists(settings_file):
        try:
            spec = importlib.util.spec_from_file_location("serversettings", settings_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Keep sys.modules clean
                spec.loader.exec_module(module)
                
                for key in DEFAULT_SETTINGS.keys():
                    if hasattr(module, key):
                        settings[key] = getattr(module, key)
                logger.info(f"Loaded server settings from {settings_file}")
        except Exception as e:
            logger.error(f"Error loading settings from {settings_file}: {e}")
            
    return settings
