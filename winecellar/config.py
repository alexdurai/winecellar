import yaml
import os
from pathlib import Path

class WinecellarConfig:
    def __init__(self, path: Path):
        self.path = path
        with open(path) as f:
            self.data = yaml.safe_load(f)
            self.features = self.data.get("features", {})
            self.backup_cfg = self.data.get("backup", {})
            self.bottle_cfg = self.data.get("bottle", {})
            self.logging_cfg = self.data.get("logging", {})

    def bottle(self):
        return self.data["bottle"]

    def section(self, name: str):
        return self.data.get(name, {})

    @staticmethod
    def expand(path: str) -> Path:
        return Path(os.path.expandvars(os.path.expanduser(path))).resolve()
