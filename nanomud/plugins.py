import os
import sys
import importlib.util
import logging

logger = logging.getLogger(__name__)

def load_plugins(engine, plugins_dir: str):
    """
    Scans plugins_dir for .py files, loads them, and runs register(engine).
    """
    try:
        os.makedirs(plugins_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create plugins directory: {e}")
        return

    # Add plugins directory to sys.path so plugins can do local relative imports
    if plugins_dir not in sys.path:
        sys.path.insert(0, plugins_dir)

    loaded_count = 0
    try:
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                plugin_name = filename[:-3]
                file_path = os.path.join(plugins_dir, filename)
                
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[plugin_name] = module
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, "register"):
                            module.register(engine)
                            logger.info(f"Loaded plugin: {plugin_name}")
                            loaded_count += 1
                        else:
                            logger.warning(f"Plugin {plugin_name} has no register(engine) function.")
                except Exception as e:
                    logger.error(f"Error loading plugin {plugin_name} from {file_path}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error scanning plugins directory: {e}")

    if loaded_count > 0:
        print(f"Loaded {loaded_count} plugin(s) from {plugins_dir}")
