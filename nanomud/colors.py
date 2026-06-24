COLOR_MAP = {
    # Normal colors
    "{r": "\033[31m",
    "{g": "\033[32m",
    "{y": "\033[33m",
    "{b": "\033[34m",
    "{m": "\033[35m",
    "{c": "\033[36m",
    "{w": "\033[37m",
    # Bold colors
    "{R": "\033[1;31m",
    "{G": "\033[1;32m",
    "{Y": "\033[1;33m",
    "{B": "\033[1;34m",
    "{M": "\033[1;35m",
    "{C": "\033[1;36m",
    "{W": "\033[1;37m",
    # Reset
    "{x": "\033[0m",
}

def ansi_format(text: str) -> str:
    """Replace nanomud color tags with ANSI escape codes."""
    for tag, code in COLOR_MAP.items():
        text = text.replace(tag, code)
    return text

def strip_colors(text: str) -> str:
    """Remove nanomud color tags."""
    for tag in COLOR_MAP.keys():
        text = text.replace(tag, "")
    return text
