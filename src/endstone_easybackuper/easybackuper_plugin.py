# Python libs
import re, os, json, shutil, zipfile, tarfile
from datetime import datetime
from pathlib import Path

# endstone libs
from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender, CommandSenderWrapper
from endstone.plugin import Plugin

# TAG: Global constants
plugin_name = "EasyBackuper"
plugin_name_smallest = "easybackuper"
plugin_description = "The simplest Python hot backup plugin based on EndStone (LeviLamina - LSE engine)."
plugin_version = "0.3.0-beta"
plugin_author = ["MengHanLOVE"]
plugin_the_help_link = "https://www.minebbs.com/resources/easybackuper-eb.7771/"
plugin_website = "https://minebbs.com"
plugin_github_link = "https://github.com/MengHanLOVE1027/EasyBackuper"
plugin_license = "AGPL-3.0"
plugin_copyright = "Please keep the original author information!"

success_plugin_version = "v" + plugin_version
plugin_full_name = plugin_name + " " + success_plugin_version

# Read server.properties
with open("./server.properties", "r") as file:
    server_properties_file = file.read()

plugin_path = Path(f"./plugins/{plugin_name}")
plugin_config_path = plugin_path / "config" / "EasyBackuper.json"
backup_tmp_path = Path("./backup_tmp")  # temporary copy/pack path
world_level_name = re.search(r"level-name=(.*)", server_properties_file).group(1)  # world name
world_folder_path = Path(f"./worlds/{world_level_name}")  # world path

# NOTE: Quiet plugin logger (only errors)
def plugin_error(server, text) -> None:
    try:
        server.logger.error(f"[{plugin_name}] {text}")
    except Exception:
        pass

# TAG: Default config file (as JSON text)
plugin_config_file = """
{
    "exe_7z_path": "./plugins/EasyBackuper/7za.exe",
    "BackupFolderPath": "./backup",
    "Auto_Clean": {
        "Use_Number_Detection": {
            "Status": true,
            "Max_Number": 10,
            "Mode": 0
        }
    },
    "Scheduled_Tasks": {
        "Status": false,
        "Cron": "*/30 * * * * *"
    },
    "Broadcast": {
        "Status": true,
        "Backup_Time_ms": 5000,
        "Title": "[OP] Backup is about to start~",
        "SubTitle": "Backup starts in 5 seconds!",
        "Server_Title": "[Server] Never Gonna Give You Up~",
        "Server_SubTitle": "Never Gonna Let You Down~",
        "Backup_success_Title": "Backup complete!",
        "Backup_success_SubTitle": "Star-level service, let love connect",
        "Backup_wrong_Title": "Backup failed",
        "Backup_wrong_SubTitle": "RT"
    },
    "Debug_MoreLogs": false,
    "Debug_MoreLogs_Player": false,
    "Debug_MoreLogs_Cron": false
}
"""

# Ensure plugin folder + config (quiet)
os.makedirs(plugin_path, exist_ok=True)
if plugin_config_path.exists():
    with open(plugin_config_path, "r", encoding="utf-8") as load_f:
        pluginConfig = json.load(load_f)
else:
    pluginConfig = json.loads(plugin_config_file)
    plugin_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(plugin_config_path, "w", encoding="utf-8") as write_f:
        write_f.write(json.dumps(pluginConfig, indent=4, ensure_ascii=False))

# TAG: Globals
(yes_no_console,) = (None,)

# Cron-related (not wired yet)
scheduled_tasks = pluginConfig["Scheduled_Tasks"]
scheduled_tasks_status = scheduled_tasks["Status"]
scheduled_tasks_cron = scheduled_tasks["Cron"]
cronExpr = scheduled_tasks_cron

# Auto-clean section
auto_cleaup = pluginConfig["Auto_Clean"]
use_number_detection = auto_cleaup["Use_Number_Detection"]
use_number_detection_status = use_number_detection.get("Status", True)
use_number_detection_max_number = int(use_number_detection.get("Max_Number", 10))
use_number_detection_mode = use_number_detection.get("Mode", 0)

# Debug flags (kept for future, but we run quiet)
Debug_MoreLogs = pluginConfig["Debug_MoreLogs"]
Debug_MoreLogs_Player = pluginConfig["Debug_MoreLogs_Player"]
Debug_MoreLogs_Cron = pluginConfig["Debug_MoreLogs_Cron"]
Cron_Use_Backup = True

my_beautiful_text = f"This is {ColorFormat.YELLOW}yellow, {ColorFormat.AQUA}aqua and {ColorFormat.GOLD}gold{ColorFormat.RESET}."

class MyZipInfo(zipfile.ZipInfo):
    # Keep UTF-8 filenames if zip is ever used elsewhere
    def _encodeFilename(self, zefilename):
        return zefilename.encode("utf-8")
zipfile.ZipInfo = MyZipInfo

# --- keep only the N newest backups for this world (quiet & safe) ---
_BACKUP_NAME_RE = re.compile(rf"^{re.escape(world_level_name)}_(\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}-\d{{2}})\.tar$")

def _list_world_backups_sorted_newest_first(folder) -> list[Path]:
    """Return list of Path objects for this world's .tar backups, newest first."""
    root = Path(folder)
    if not root.exists():
        return []
    items = []
    for f in root.glob(f"{world_level_name}_*.tar"):
        dt = None
        m = _BACKUP_NAME_RE.match(f.name)
        if m:
            try:
                dt = datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M-%S")
            except Exception:
                dt = None
        if dt is None:
            try:
                dt = datetime.fromtimestamp(f.stat().st_mtime)
            except Exception:
                dt = datetime.min
        items.append((f, dt))
    items.sort(key=lambda t: t[1], reverse=True)
    return [p for p, _ in items]

def _cleanup_old_backups(server, folder, max_keep: int = 10) -> None:
    """Delete oldest backups beyond max_keep; logs one summary line."""
    try:
        files = _list_world_backups_sorted_newest_first(folder)
        if len(files) <= max_keep:
            return
        removed = 0
        for stale in files[max_keep:]:
            try:
                stale.unlink()
                removed += 1
            except Exception as e:
                plugin_error(server, f"Cleanup failed for '{stale}': {e}")
        try:
            server.logger.info(f"[{plugin_name}] Cleanup: kept {max_keep}, removed {removed}.")
        except Exception:
            pass
    except Exception as e:
        plugin_error(server, f"Cleanup pass failed: {e}")

# Simple helper to chat like /say (no titles)
def _say(server, msg: str) -> None:
    try:
        server.dispatch_command(server.command_sender, f'say {msg}')
    except Exception:
        # Fallback: broadcast to anyone allowed; still chat-only
        try:
            server.broadcast(msg, "easybackuper_plugin.command.players")
        except Exception:
            pass

# TAG: Plugin entry point
class EasyBackuperPlugin(Plugin):
    """
    Plugin entry point
    """

    api_version = "0.11"

    full_name = plugin_full_name
    description = plugin_description
    version = plugin_version
    authors = plugin_author
    website = plugin_website

    # NOTE: Register command (explicit variants to avoid parser errors)
    commands = {
        "backup": {
            "description": "Create a hot backup (console or OP).",
            "usages": ["/backup", "/backup <init>", "/backup <reload>"],
            "permissions": ["easybackuper_plugin.command.only_op"],
        }
    }

    # NOTE: Permissions
    permissions = {
        "easybackuper_plugin.command.only_op": {
            "description": "Only OP Players can use this command",
            "default": "op",
        },
        "easybackuper_plugin.command.players": {
            "description": "All Players can see backup chat messages",
            "default": "true",
        },
    }

    def __init__(self):
        super().__init__()
        self.last_death_locations = {}

    # NOTE: Backup part #2 (does the actual snapshot + archive)
    def backup_2(plugin: Plugin) -> None:
        """
        Backup part 2 (quiet; only errors; emits one success message on completion)
        """
        server = plugin.server

        # 1) Freeze writes
        if not server.dispatch_command(server.command_sender, "save hold"):
            plugin_error(server, "Failed to issue 'save hold'.")
            return

        def save_query():
            messages = []

            sender = CommandSenderWrapper(
                server.command_sender,
                on_message=lambda msg: messages.append(
                    msg.params if hasattr(msg, 'params') else [str(msg)]
                ),
            )

            # 2) Flush and get file offsets from Bedrock
            ready = server.dispatch_command(sender, "save query")
            if not ready:
                plugin_error(server, "'save query' not ready; resuming saves.")
                server.dispatch_command(server.command_sender, "save resume")
                _say(server, f"§c[{plugin_name}] Backup failed: save query not ready.")
                return

            # Prepare temp folder
            if backup_tmp_path.exists():
                try:
                    shutil.rmtree(backup_tmp_path)
                except Exception:
                    pass
            try:
                os.mkdir(backup_tmp_path)
            except Exception as e:
                plugin_error(server, f"Temp dir creation failed: {e}")
                server.dispatch_command(server.command_sender, "save resume")
                _say(server, f"§c[{plugin_name}] Backup failed: cannot create temp dir.")
                return

            # 3) Copy the world (frozen view)
            #    Skip resource_packs/ and behavior_packs/ — they are static
            #    assets locked by BDS and recoverable without backup.
            def _ignore_packs(directory, contents):
                if directory.replace("\\", "/").rstrip("/").endswith(world_level_name):
                    skip = {c for c in contents if c in ("resource_packs", "behavior_packs")}
                    if skip:
                        try:
                            server.logger.info(f"[{plugin_name}] Skipping locked dirs: {skip}")
                        except Exception:
                            pass
                    return skip
                return set()

            def _safe_copy2(src, dst):
                """Copy a single file, logging and skipping on PermissionError."""
                try:
                    shutil.copy2(src, dst)
                except PermissionError:
                    try:
                        server.logger.warning(f"[{plugin_name}] Skipped (locked): {src}")
                    except Exception:
                        pass

            try:
                shutil.copytree(
                    world_folder_path,
                    backup_tmp_path / world_level_name,
                    ignore=_ignore_packs,
                    copy_function=_safe_copy2,
                )
            except Exception as e:
                plugin_error(server, f"Copy failed: {e}")
                server.dispatch_command(server.command_sender, "save resume")
                _say(server, f"§c[{plugin_name}] Backup failed during copy.")
                return

            # 4) Resume writes ASAP
            server.dispatch_command(server.command_sender, "save resume")

            # Expect file list in messages[1][0]; if shape changes, proceed best-effort
            try:
                file_paths = messages[1][0].split(", ")
            except Exception:
                file_paths = []

            # Trim files to offsets (Bedrock reports final sizes)
            def truncate_file(file_path, position):
                try:
                    with open(file_path, "r+") as file:
                        original_size = file.seek(0, os.SEEK_END)
                        file.seek(position)
                        file.truncate()
                        new_size = file.seek(0, os.SEEK_END)
                        size_difference = original_size - new_size
                        if size_difference != 0:
                            server.logger.warning(f"[{plugin_name}] File size changed: {size_difference} bytes")
                        return True
                except Exception as e:
                    plugin_error(server, f"Error truncating file '{file_path}': {e}")
                    return False

            for path in file_paths:
                try:
                    file_name, position = path.split(":")
                    position = int(position)
                    real_file_name = backup_tmp_path / file_name
                    truncate_file(real_file_name, position)
                except Exception:
                    # ignore malformed entries quietly
                    pass

            # 5) Pack the temp snapshot as .tar with timestamp
            tmp_root = str(backup_tmp_path)
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            tar_file_new = os.path.join(
                pluginConfig["BackupFolderPath"], f"{world_level_name}_{ts}.tar"
            )

            archiving_ok = True
            try:
                os.makedirs(pluginConfig["BackupFolderPath"], exist_ok=True)
                with tarfile.open(tar_file_new, "w") as tar:
                    for dir_path, _dir_names, file_names in os.walk(tmp_root):
                        rel_base = dir_path.replace(tmp_root, "", 1).lstrip(os.sep)
                        for filename in file_names:
                            full_path = os.path.join(dir_path, filename)
                            arcname = os.path.join(rel_base, filename) if rel_base else filename
                            tar.add(full_path, arcname=arcname)
            except Exception as e:
                archiving_ok = False
                plugin_error(server, f"Archiving failed: {e}")
            finally:
                # Cleanup temp snapshot
                try:
                    if backup_tmp_path.exists():
                        shutil.rmtree(backup_tmp_path)
                except Exception as e:
                    server.logger.warning(f"[{plugin_name}] Temp cleanup warning: {e}")

            # 6) Success/Failure chat + cleanup rotation
            if archiving_ok:
                try:
                    server.logger.info(f"[{plugin_name}] Backup complete: {tar_file_new}")
                except Exception:
                    pass

                # Chat success messages (no titles)
                try:
                    bc = pluginConfig.get("Broadcast", {})
                    _say(server, f"§2[{plugin_name}] {bc.get('Backup_success_Title', 'Backup complete!')}")
                    sub = bc.get("Backup_success_SubTitle", "")
                    if sub:
                        _say(server, f"§a{sub}")
                except Exception:
                    pass

                # Enforce: keep only newest N backups for this world
                max_keep = use_number_detection_max_number if use_number_detection_status else 10
                _cleanup_old_backups(server, pluginConfig["BackupFolderPath"], max_keep=max_keep)
            else:
                try:
                    bc = pluginConfig.get("Broadcast", {})
                    _say(server, f"§c[{plugin_name}] {bc.get('Backup_wrong_Title', 'Backup failed')}")
                    sub = bc.get("Backup_wrong_SubTitle", "")
                    if sub:
                        _say(server, f"§c{sub}")
                except Exception:
                    pass

        server.scheduler.run_task(plugin, save_query, delay=20, period=0)
        return None

    # NOTE: Backup part #1 (chat announce + schedule part #2)
    def backup(self) -> None:
        """
        Backup entry (quiet; no player spam beyond chat)
        """
        self.server.scheduler.run_task(self, self.backup_2, delay=20, period=0)
        return None

    # NOTE: Player/server notifications (chat) — guarded & skip if disabled
    def notice(self) -> bool:
        """
        Notification flow (chat-only if Broadcast.Status is true)
        """
        global yes_no_console

        broadcast = pluginConfig["Broadcast"]
        if not broadcast.get("Status", True):
            # go straight to backup quietly
            self.server.scheduler.run_task(self, self.backup, delay=0, period=0)
            return True

        ms = int(broadcast.get("Backup_Time_ms", 5000))
        title = broadcast.get("Title", "Backup is about to start~")
        sub   = broadcast.get("SubTitle", "Backup starts in 5 seconds!")
        server_title = broadcast.get("Server_Title", "[Server] Never Gonna Give You Up~")
        server_sub   = broadcast.get("Server_SubTitle", "Never Gonna Let You Down~")

        # Chat announce (no titles/subtitles)
        if yes_no_console == 0:
            _say(self.server, f"§e{title}")
            if sub:
                _say(self.server, f"§7{sub}")
        else:
            _say(self.server, f"§e{server_title}")
            if server_sub:
                _say(self.server, f"§7{server_sub}")

        # Schedule backup() once after the configured delay (ms → ticks)
        self.server.scheduler.run_task(
            self, self.backup, delay=int(ms / 1000 * 20), period=0
        )
        return True

    # NOTE: Entry for /backup — determines sender and kicks off notice()
    def start(self, sender) -> bool:
        """
        Start (quiet)
        """
        global yes_no_console

        if getattr(sender, "name", "") == "Server":
            yes_no_console = 1
            self.notice()
            return True
        elif isinstance(sender, Player):
            yes_no_console = 0
            self.notice()
            return True
        else:
            self.server.command_sender.send_error_message(
                "This command can only be executed by a player or console!"
            )
            return False

    # TAG: Command handler
    def on_command(self, sender: CommandSender, command: Command, args) -> bool:
        global pluginConfig

        if command.name == "backup":
            if len(args) == 0:
                self.start(sender)
            else:
                subcmd = (args[0] or "").lower()
                if subcmd == "init":
                    try:
                        pluginConfig = json.loads(plugin_config_file)
                        with open(plugin_config_path, "w", encoding="utf-8") as write_f:
                            write_f.write(json.dumps(pluginConfig, indent=4, ensure_ascii=False))
                        _say(self.server, f"[{plugin_name}] Config reset to defaults.")
                    except Exception as e:
                        plugin_error(self.server, f"Init failed: {e}")
                elif subcmd == "reload":
                    try:
                        with open(plugin_config_path, "r", encoding="utf-8") as load_f:
                            pluginConfig = json.load(load_f)
                        _say(self.server, f"[{plugin_name}] Config reloaded.")
                    except Exception as e:
                        plugin_error(self.server, f"Reload failed: {e}")
                else:
                    self.start(sender)
        return True

    # TAG: on_load — quiet
    def on_load(self) -> None:
        pass

    def on_disable(self) -> None:
        try:
            self.server.scheduler.cancel_tasks(self)
        except Exception as e:
            plugin_error(self.server, f"on_disable cleanup error: {e}")
