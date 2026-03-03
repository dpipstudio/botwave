import os
import re
import shlex
from typing import Dict


class EnvManager:
    """Manages environment variables with support for .env files and typed access."""

    def __init__(self):
        filepath = self.get("DOTENV_PATH", ".env")
        self.load(filepath)

    def load(self, filepath: str = ".env") -> None:
        """Load environment variables from a .env file into os.environ."""
        if not os.path.exists(filepath):
            return

        dotenv = self.__load_env(filepath)
        os.environ.update(dotenv)

    def get(self, key: str, default = None, get_immutability: bool = False, strip_immutable: bool = True) -> tuple | str | None:
        """Return the value of a key case-insensitively, or default if not found.
        
        If get_immutability is True, returns a (value, is_immutable) tuple instead.
        """

        key_lower = key.lower()

        for k, v in os.environ.items():
            if k.lower() == key_lower:
                stripped_v = self.__strip_immutable(v) if strip_immutable else v
                immutable = stripped_v != v

                if get_immutability:
                    return (stripped_v, immutable)

                return stripped_v

        if get_immutability:
            return (default, False)
        
        return default

    def set(self, key: str, value: str, immutable: bool = False) -> None:
        """
        Set an environment variable. If immutable=True, the value is locked
        and future changes will raise a ValueError.
        """

        value = str(value)

        if immutable:
            value = f"immutable({value})"

        else:
            if self.__is_immutable(key):
                raise ValueError(
                    f"Provided key ({key}) is immutable. Changes are not recommended, "
                    "but can be done by replacing it with another immutable string. "
                    "Consider yourself warned."
                )

        os.environ[key.upper()] = value

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Return the value of a key as an integer, or default if missing or invalid."""

        value = self.get(key)

        try:
            return int(value) if value is not None else default
        
        except ValueError:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Return the value of a key as a boolean, or default if missing."""

        value = self.get(key)

        if value is None:
            return default

        return value.lower() in ("1", "true", "yes", "on", "absolutely!")

    def __load_env(self, filepath: str) -> Dict[str, str]:
        """Parse a .env file and return a dict of key-value pairs."""

        env_dict = {}

        try:
            with open(filepath, "r") as file:
                for line in file:
                    line = line.strip()

                    if not line or line.startswith("#"):
                        continue

                    key, value = line.split("=", 1)
                    value = value.strip()
                    env_dict[key.strip()] = shlex.split(value)[0] if value else ""

        except Exception:
            pass

        return env_dict

    def __is_immutable(self, key: str) -> bool:
        """Return True if the key's value is marked as immutable."""

        value = self.get(key, strip_immutable=False)

        if value is None:
            return False

        return bool(re.match(r"immutable\((.*?)\)", value))

    def __strip_immutable(self, text: str) -> str:
        """Strip the immutable() wrapper from a value if present."""

        match = re.fullmatch(r"immutable\((.*?)\)", text)

        if match:
            return match.group(1)

        return text


Env = EnvManager()