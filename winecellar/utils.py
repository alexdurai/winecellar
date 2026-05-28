import subprocess
import os

class CommandRunner:
    @staticmethod
    def run(cmd, env=None):
        print(">>", " ".join(cmd))
        #cmd.insert(1, f"--config={os.environ['BOTTLES_CONFIG_DIR']}")
        #cmd.insert(1, f"--config={os.environ['BOTTLES_DATA_DIR']}")
        subprocess.run(cmd, check=True, env=env)
