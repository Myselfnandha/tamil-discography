#!/usr/bin/env python3
"""
mcp.py — Antigravity Dynamic On-Demand MCP Server Manager.

Manages zero-default, on-demand activation and auto-shutdown of MCP servers
to preserve system memory, CPU, and eliminate background startup errors.

Usage:
  python mcp.py list                    # List catalog servers & active status
  python mcp.py enable <name>...        # Enable server(s) on-demand
  python mcp.py disable <name>...       # Disable / auto-close server(s)
  python mcp.py reset                   # Reset to zero-default clean profile ({})
  python mcp.py run <name> -- <cmd>     # Ephemeral run with auto-shutdown
  python mcp.py status                  # Show current active MCP servers
"""

import os
import sys
import json
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(SCRIPT_DIR)
WORKSPACE_ROOT = os.path.dirname(AGENT_DIR)
REGISTRY_FILE = os.path.join(AGENT_DIR, "mcp-registry", "servers.json")
LOCAL_CONFIG = os.path.join(AGENT_DIR, "mcp_config.json")
GLOBAL_CONFIG = os.path.expanduser("~/.gemini/config/mcp_config.json")


def load_json(path, default=None):
    if not os.path.exists(path):
        return default or {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading {path}: {e}", file=sys.stderr)
        return default or {}


def save_json(path, data):
    dir_path = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_path, exist_ok=True)
    temp_path = f"{path}.tmp.{os.getpid()}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def get_target_configs(target_mode):
    if target_mode == "global":
        return [GLOBAL_CONFIG]
    elif target_mode == "all":
        return [LOCAL_CONFIG, GLOBAL_CONFIG]
    else:
        return [LOCAL_CONFIG]


def cmd_list(args):
    registry = load_json(REGISTRY_FILE, {"mcpServers": {}}).get("mcpServers", {})
    local_cfg = load_json(LOCAL_CONFIG, {"mcpServers": {}}).get("mcpServers", {})
    global_cfg = load_json(GLOBAL_CONFIG, {"mcpServers": {}}).get("mcpServers", {})

    print("\n" + "=" * 70)
    print("🔌 ANTIGRAVITY MCP SERVER CATALOG & RUNTIME STATUS")
    print("=" * 70)
    print(f"{'SERVER NAME':<18} {'CATEGORY':<14} {'LOCAL':<10} {'GLOBAL':<10} {'DESCRIPTION'}")
    print("-" * 70)

    for name, info in sorted(registry.items()):
        is_local = "✅ ON" if name in local_cfg else "⚪ off"
        is_global = "✅ ON" if name in global_cfg else "⚪ off"
        cat = info.get("category", "general")
        desc = info.get("description", "")
        print(f"{name:<18} {cat:<14} {is_local:<10} {is_global:<10} {desc[:35]}")

    print("-" * 70)
    active_count = len(local_cfg)
    print(f"Active in Local  : {active_count} / {len(registry)} servers")
    print(f"Active in Global : {len(global_cfg)} / {len(registry)} servers")
    print("\nCommands:")
    print("  Enable  : python .agents/scripts/mcp.py enable <name>")
    print("  Disable : python .agents/scripts/mcp.py disable <name>")
    print("  Reset   : python .agents/scripts/mcp.py reset (zero-default)\n")


def resolve_placeholders(obj):
    if isinstance(obj, str):
        home = os.path.expanduser("~")
        return obj.replace("${HOME}", home).replace("${AGENT_DIR}", AGENT_DIR).replace("${WORKSPACE_ROOT}", WORKSPACE_ROOT)
    elif isinstance(obj, list):
        return [resolve_placeholders(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: resolve_placeholders(v) for k, v in obj.items()}
    return obj


def cmd_enable(args):
    registry = load_json(REGISTRY_FILE, {"mcpServers": {}}).get("mcpServers", {})
    target_paths = get_target_configs(args.target)

    for name in args.names:
        if name not in registry:
            print(f"❌ Error: MCP server '{name}' not found in registry (.agents/mcp-registry/servers.json).", file=sys.stderr)
            continue

        server_def = {k: resolve_placeholders(v) for k, v in registry[name].items() if k not in ("description", "category")}

        for cfg_path in target_paths:
            cfg = load_json(cfg_path, {"mcpServers": {}})
            if "mcpServers" not in cfg:
                cfg["mcpServers"] = {}
            cfg["mcpServers"][name] = server_def
            save_json(cfg_path, cfg)
            print(f"✅ Enabled [{name}] in {cfg_path}")


def cmd_disable(args):
    target_paths = get_target_configs(args.target)

    for name in args.names:
        for cfg_path in target_paths:
            cfg = load_json(cfg_path, {"mcpServers": {}})
            if "mcpServers" in cfg and name in cfg["mcpServers"]:
                del cfg["mcpServers"][name]
                save_json(cfg_path, cfg)
                print(f"🛑 Disabled [{name}] from {cfg_path} (auto-closed background process)")
            else:
                print(f"⚪ [{name}] was not active in {cfg_path}")


def cmd_reset(args):
    target_paths = get_target_configs(args.target)
    for cfg_path in target_paths:
        save_json(cfg_path, {"mcpServers": {}})
        print(f"🧹 Reset {cfg_path} to clean zero-default profile (0 active servers).")


def cmd_run(args):
    """Enable server ephemerally, run command, and disable immediately."""
    name = args.name
    command = args.command
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        print("❌ Error: No command specified after '--'.", file=sys.stderr)
        sys.exit(1)

    print(f"⚡ Ephemerally activating [{name}] for command execution...")
    cmd_enable(argparse.Namespace(names=[name], target=args.target))

    try:
        ret = subprocess.call(command)
    finally:
        print(f"\n🔒 Auto-closing [{name}] after task completion...")
        cmd_disable(argparse.Namespace(names=[name], target=args.target))

    sys.exit(ret)


def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-g", "--global", dest="target", action="store_const", const="global", default="local",
                               help="Target global config (~/.gemini/config/mcp_config.json)")
    parent_parser.add_argument("-a", "--all", dest="target", action="store_const", const="all",
                               help="Target both local and global configs")

    parser = argparse.ArgumentParser(
        description="Antigravity Dynamic On-Demand MCP Server Manager",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list / status
    p_list = subparsers.add_parser("list", parents=[parent_parser], help="List all cataloged and active MCP servers")
    p_list.set_defaults(func=cmd_list)

    p_status = subparsers.add_parser("status", parents=[parent_parser], help="Show active MCP server status")
    p_status.set_defaults(func=cmd_list)

    # enable
    p_enable = subparsers.add_parser("enable", parents=[parent_parser], help="Enable one or more MCP servers on demand")
    p_enable.add_argument("names", nargs="+", help="Names of MCP servers to enable")
    p_enable.set_defaults(func=cmd_enable)

    # disable
    p_disable = subparsers.add_parser("disable", parents=[parent_parser], help="Disable and auto-close one or more MCP servers")
    p_disable.add_argument("names", nargs="+", help="Names of MCP servers to disable")
    p_disable.set_defaults(func=cmd_disable)

    # reset
    p_reset = subparsers.add_parser("reset", parents=[parent_parser], help="Reset to zero-default profile (empty active servers)")
    p_reset.set_defaults(func=cmd_reset)

    # run
    p_run = subparsers.add_parser("run", parents=[parent_parser], help="Ephemerally enable server, run command, and auto-close")
    p_run.add_argument("name", help="Name of MCP server")
    p_run.add_argument("command", nargs=argparse.REMAINDER, help="Command to run")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
