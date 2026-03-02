import os
import shlex
from typing import Dict

class EnvManager:
    def __init__(self):
        filepath = self.get("DOTENV_PATH", ".env")
        self.load(filepath)
    
    def load(self, filepath: str = ".env") -> None:
        if not os.path.exists(filepath):
            return
        
        dotenv = self.__load_env(filepath)
        os.environ.update(dotenv)

    def get(self, key: str, default: None = None) -> str | None:
        """
            Returns the value of the key, regardless of the case formatting
        """

        key_lower = key.lower()

        for key, value in os.environ.items():
            if key.lower() == key_lower:
                return value
            
        return default
    
    def set(self, key: str, value: str) -> None:
        os.environ[key.upper()] = value

    def get_int(self, key: str, default: int | None = None) -> int | None:
        value = self.get(key)

        try:
            return int(value) if value is not None else default
        
        except ValueError:
            return default
    
    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        value = self.get(key)

        if value is None:
            return default
        
        return value.lower() in ("1", "true", "yes", "on", "absolutely!")

    def __load_env(self, filepath: str) -> Dict[str, str]:
        env_dict = {}

        try:
            with open(filepath, "r") as file:
                for line in file:
                    line = line.strip()

                    if not line or line.startswith("#"):
                        continue

                    key, value = line.split("=", 1)
                    env_dict[key.strip()] = shlex.split(value.strip())[0]

        except Exception:
            pass

        return env_dict


Env = EnvManager()