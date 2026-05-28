import shutil
import tarfile
import os
from pathlib import Path
from datetime import datetime
import json
import subprocess
from .utils import CommandRunner
from .log import WinecellarLogger

class Bottle:
    def __init__(self, cfg):
        self.cfg = cfg
        self.data = cfg.data
        self.bottle_cfg = self.data.get("bottle", {})
        self.backup_cfg = self.data.get("backup", {})
        self.features = self.data.get("features", {})
        self.graphics = self.data.get("graphics", {})
        self.vkd3d = self.get_installed_vkd3d_versions()
        self.run = CommandRunner.run
        self.log = WinecellarLogger(cfg).get_logger()
    
        self.name = self.bottle_cfg["name"]
        self.location = Path(
            self.bottle_cfg.get("location", "~/.local/share/bottles")
        ).expanduser()

        # SAFETY: location must be parent dir
        if self.location.name == self.name:
            raise ValueError(
                "Bottle location must be the parent directory, not the bottle directory itself"
            )

        self.bottle_dir = self.location / self.name


    def edit_bottle_cli(self):
        """
        Helper to run bottles-cli edit with a list of arguments.
        """
        args = []
        if self.vkd3d:
            args += ["--vkd3d", self.vkd3d]

        cmd = ["bottles-cli", "edit", "-b", self.name] + args

        self.run(cmd)

    def bottle_exists(self) -> bool:
        """
        Check if bottle exists according to Bottles.
        """
        try:
            result = subprocess.run(
                ["bottles-cli", "list", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )
            bottles = json.loads(result.stdout)
            return any(b["name"] == self.name for b in bottles)
        except Exception:
            # Fallback to disk check only
            return self.bottle_dir.exists()


    def apply_drive_mappings(self):
        drives = self.cfg.data.get("drives", {})
        if not drives:
            return

        for letter, cfg in drives.items():
            path = cfg["path"]
            drive_type = cfg.get("type", "hd")
            readonly = cfg.get("readonly", False)

            cmd = [
                "bottles-cli",
                "drive",
                "add",
                "-b", self.name,
                "--letter", letter,
                "--path", path,
                "--type", drive_type,
            ]

            if readonly:
                cmd.append("--readonly")

            self.log.info("Mapping drive %s → %s", letter, path)
            self.run(cmd)

    def assign_vk3d_version(self):
        # ---------------- VKD3D ----------------
        
        installed_versions = self.get_installed_vkd3d_versions()
        vkd3d_installed = installed_versions.get(self.name)
        vkd3d_requested = self.cfg.data.get("graphics", {}).get("vkd3d_version", "default")

        if vkd3d_requested == "default":
            if vkd3d_installed:
                vkd3d = vkd3d_installed
            else:
                self.log.warning("No VKD3D versions installed for bottle %s", self.name)
                vkd3d = None
        else:
            if vkd3d_installed == vkd3d_requested:
                vkd3d = vkd3d_requested
            else:
                self.log.warning(
                    "Requested VKD3D version '%s' not installed, skipping", vkd3d_requested
                )
                vkd3d = None

        return vkd3d

    def apply_dpi_settings(self):
        dpi_cfg = self.cfg.data.get("dpi", {})
        if not dpi_cfg.get("enabled", False):
            return

        dpi = dpi_cfg.get("scale", 96)

        reg = self.bottle_dir / "dpi.reg"

        reg.write_text(
            f"""Windows Registry Editor Version 5.00

    [HKCU\\Control Panel\\Desktop]
    "LogPixels"=dword:{dpi:08x}
    "Win8DpiScaling"=dword:00000001
    """
        )

        self.log.info("Applying DPI scaling: %s", dpi)

        self.run([
            "bottles-cli", "run",
            "-b", self.name,
            "--", "regedit", str(reg)
        ])

    def apply_environment(self):
        
        env_cfg = self.cfg.data.get("environment", {})
        if not env_cfg.get("enabled", False):
            return

        env_vars = env_cfg.get("variables", {})
        for key, value in env_vars.items():
            self.log.info("Setting environment variable: %s=%s", key, value)
            self.run([
                "bottles-cli", "env", "set",
                "-b", self.name,
                "--key", key,
                "--value", value,
            ])
    def apply_dll_overrides(self, dry_run=False):
            dll_cfg = self.cfg.data.get("dll_overrides", {})
            mode = dll_cfg.get("mode")
            for dll in dll_cfg.get("dlls", []):
                cmd = [
                    "bottles-cli", "reg", "add",
                    "-b", self.name,
                    "-k", "HKCU\\Software\\Wine\\DllOverrides",
                    "-v", dll,
                    "-d", mode,
                    "-t", "REG_SZ",
                ]
                if dry_run:
                    self.log.info("[DRY-RUN] %s", " ".join(cmd))
                else:
                    self.run(cmd)

    def install_dependencies(self):
        deps = self.bottle_cfg.get("dependencies", [])
        if not deps:
            return

        for dep in deps:
            self.log.info("Installing dependency: %s", dep)
            self.run([
                "bottles-cli", "deps", "install",
                "-b", self.name,
                "--dep", dep,
            ])

    def edit_bottle(self, args):
        """
        Helper to run bottles-cli edit with a list of arguments.
        """
        cmd = ["bottles-cli", "edit", "-b", self.name] + args

        self.run(cmd)

    def get_installed_vkd3d_versions(self):
        import json
        result = subprocess.run(
            ["bottles-cli", "-j", "list", "bottles"],
            capture_output=True,
            text=True,
            check=True
        )
        bottles = json.loads(result.stdout)  # this is now a dict

        versions = {}
        for name, info in bottles.items():  # key=name, value=dict
            versions[name] = info.get("VKD3D")
        return versions



    # ---------------- CREATE ----------------

    def create(self, dry_run=False):
        if self.bottle_exists():
            raise RuntimeError(f"Bottle '{self.name}' already exists")

        # Map features → environment
        environment = self.bottle_cfg.get("environment", "gaming" if self.features.get("dxvk") or self.features.get("vkd3d") else "application")

        cmd = [
            "bottles-cli", "new",
            "--bottle-name", self.name,
            "--environment", environment,
            "--arch", self.bottle_cfg.get("arch", "win64"),
            "--runner", self.bottle_cfg.get("runner", "soda"),
        ]

        # Optional feature flags
        if self.features.get("dxvk") and "dxvk" in self.data.get("graphics", {}):
            cmd += ["--dxvk", str(self.data["graphics"]["dxvk_version"])]

        if self.features.get("vkd3d"):
            cmd += ["--vkd3d", str(self.data["graphics"].get("vkd3d_version", "default"))]

        if dry_run:
            self.log.info("[DRY-RUN] %s", " ".join(cmd))
            return

        self.log.info("Creating bottle '%s' with environment '%s'", self.name, environment)
        self.run(cmd)


    # ----------------- UPDATE -----------------

    def update(self, dry_run=False):
        """
        Apply updates to an existing bottle based on the YAML configuration.
        Features, DLL overrides, environment variables, and dependencies
        will be updated. Uses correct bottles-cli commands.
        """
        cfg = self.data


        # In update()

        # ---------------- Drive mappings ----------------
        self.apply_drive_mappings() 
        # ---------------- DPI settings ----------------
        self.apply_dpi_settings()
        # ---------------- Environment variables ----------------
        self.apply_environment()
        # ---------------- DLL overrides ----------------
        self.apply_dll_overrides()
        # ---------------- Dependencies ----------------
        self.install_dependencies() 
        # ---------------- Runner ----------------
        runner = cfg["bottle"].get("runner")
        if runner:
            self.edit_bottle(["--runner", runner])

        # ---------------- Windows version ----------------
        winver = cfg["bottle"].get("windows_version")
        if winver:
            self.edit_bottle(["--win", winver])

        # ---------------- DXVK ----------------
        if cfg.get("features", {}).get("dxvk"):
            dxvk = cfg.get("graphics", {}).get("dxvk_version")
            if dxvk:
                self.edit_bottle(["--dxvk", dxvk])



        # ---------------- NVAPI ----------------
        nvapi = cfg.get("graphics", {}).get("nvapi_version")
        if nvapi:
            self.edit_bottle(["--nvapi", nvapi])

        # ---------------- Environment variables ----------------
        env_vars = cfg.get("environment", {})
        for key, value in env_vars.items():
            cmd = [
                "bottles-cli", "reg", "add",
                "-b", self.name,
                "-k", "HKCU\\Software\\Wine\\Environment",
                "-v", key,
                "-d", str(value),
                "-t", "REG_SZ",
            ]
            if dry_run:
                self.log.info("[DRY-RUN] %s", " ".join(cmd))
            else:
                self.run(cmd)

        # ---------------- DLL overrides ----------------
        
        # ---------------- Dependencies ----------------
        for dep in self.bottle_cfg.get("dependencies", []):
            self.log.info("Installing dependency: %s", dep)
            if not dry_run:
                self.run([
                    "bottles-cli", "deps", "install",
                    "-b", self.name,
                    "--dep", dep,
                ])
            else:
                self.log.info("[DRY-RUN] bottles-cli deps install -b %s --dep %s", self.name, dep)




    # ---------------- BACKUP ----------------

    def backup(self, dry_run=False):
        if not self.backup_cfg.get("enabled", True):
            return

        backup_root = Path(
            self.backup_cfg.get("path", "~/Backups/winecellar")
        ).expanduser()
        backup_root.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = f"{self.name}_{ts}"

        archive = backup_root / f"{tag}.tar.zst"

        if dry_run:
            print(f"[DRY-RUN] Backup {self.bottle_dir} → {archive}")
            return

        with tarfile.open(archive, "w:xz") as tar:
            tar.add(self.bottle_dir, arcname=self.name)

        self._prune_backups(backup_root)

    # ---------------- RESTORE ----------------

    def restore(self, backup_tag=None, dry_run=False):
        backup_root = Path(
            self.backup_cfg.get("path", "~/Backups/winecellar")
        ).expanduser()

        if backup_tag:
            archive = backup_root / f"{backup_tag}.tar.zst"
        else:
            archives = sorted(backup_root.glob(f"{self.name}_*.tar.zst"))
            if not archives:
                raise RuntimeError("No backups found")
            archive = archives[-1]

        if dry_run:
            print(f"[DRY-RUN] Restore {archive} → {self.location}")
            return

        if self.bottle_dir.exists():
            shutil.rmtree(self.bottle_dir)

        with tarfile.open(archive, "r:*") as tar:
            tar.extractall(self.location)

    # ---------------- UTIL ----------------

    def _prune_backups(self, backup_root: Path):
        keep = int(self.backup_cfg.get("keep_last", 5))
        backups = sorted(backup_root.glob(f"{self.name}_*.tar.zst"))

        for old in backups[:-keep]:
            old.unlink()
