# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Doctor — environment diagnostics."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fsq_mac.models import Response, ErrorCode, success_response, error_response


STATE_DIR = Path.home() / ".fsq-mac"


def _check_accessibility() -> dict:
    """Check if macOS Accessibility permission is likely granted."""
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first process'],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if result.returncode == 0:
            return {"name": "accessibility_permission", "status": "pass"}
        return {
            "name": "accessibility_permission",
            "status": "fail",
            "detail": "Accessibility permission not granted",
            "fix": "System Preferences → Privacy & Security → Accessibility → enable your terminal",
        }
    except Exception as exc:
        return {
            "name": "accessibility_permission",
            "status": "fail",
            "detail": str(exc),
        }


def _check_appium_server(server_url: str = "http://127.0.0.1:4723") -> dict:
    """Check if Appium server is reachable."""
    try:
        import httpx
        r = httpx.get(f"{server_url}/status", timeout=5)
        if r.status_code == 200:
            return {"name": "appium_server", "status": "pass", "detail": server_url}
        return {
            "name": "appium_server",
            "status": "fail",
            "detail": f"HTTP {r.status_code} from {server_url}",
            "fix": "Run: appium",
        }
    except Exception:
        return {
            "name": "appium_server",
            "status": "fail",
            "detail": f"Cannot reach {server_url}",
            "fix": "Run: appium",
        }


def _check_mac2_driver() -> dict:
    """Check if Appium Mac2 driver is installed."""
    try:
        result = subprocess.run(
            ["appium", "driver", "list", "--installed", "--json"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "mac2" in data or "mac2" in str(data).lower():
                return {"name": "mac2_driver", "status": "pass", "detail": "installed"}
        return {
            "name": "mac2_driver",
            "status": "fail",
            "detail": "Mac2 driver not found",
            "fix": "Run: appium driver install mac2",
        }
    except FileNotFoundError:
        return {
            "name": "mac2_driver",
            "status": "fail",
            "detail": "appium command not found",
            "fix": "Run: npm install -g appium && appium driver install mac2",
        }
    except Exception as exc:
        return {
            "name": "mac2_driver",
            "status": "fail",
            "detail": str(exc),
        }


def _check_config() -> dict:
    """Check if config file exists."""
    config_file = STATE_DIR / "config.json"
    if config_file.exists():
        return {"name": "config_file", "status": "pass", "detail": str(config_file)}
    return {
        "name": "config_file",
        "status": "warn",
        "detail": f"{config_file} not found (defaults will be used)",
    }


def _check_xcode_first_launch() -> dict:
    """Check if Xcode has completed first-launch initialization."""
    try:
        result = subprocess.run(
            ["xcodebuild", "-checkFirstLaunchStatus"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0:
            return {"name": "xcode_first_launch", "status": "pass"}
        return {
            "name": "xcode_first_launch",
            "status": "fail",
            "detail": "Xcode first launch setup incomplete",
            "fix": "Run: xcodebuild -runFirstLaunch",
        }
    except FileNotFoundError:
        return {
            "name": "xcode_first_launch",
            "status": "fail",
            "detail": "xcodebuild not found",
            "fix": "Install Xcode Command Line Tools: xcode-select --install",
        }
    except Exception as exc:
        return {
            "name": "xcode_first_launch",
            "status": "fail",
            "detail": str(exc),
        }


def _discover_doctor_plugins():
    """Load doctor checks from 'fsq_mac.doctor' entry point group."""
    from importlib.metadata import entry_points
    eps = entry_points(group="fsq_mac.doctor")
    plugins = []
    for ep in eps:
        try:
            plugins.append({"name": ep.name, "check": ep.load()})
        except Exception:
            pass
    return plugins


def check_plugins(config=None):
    """List all discovered plugins (adapters and doctor checks)."""
    from fsq_mac.adapters import available_backends
    doctor_plugins = _discover_doctor_plugins()
    return {
        "adapters": available_backends(),
        "doctor_plugins": [p["name"] for p in doctor_plugins],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_checks(core=None, scope: str = "all") -> Response:
    """Run diagnostic checks and return a Response."""
    checks: list[dict] = []

    if scope in ("all", "permissions"):
        checks.append(_check_accessibility())

    if scope in ("all", "backend"):
        # Read server_url from config file first, adapter as override (#14)
        server_url = "http://127.0.0.1:4723"
        config_file = STATE_DIR / "config.json"
        if config_file.exists():
            try:
                cfg = json.loads(config_file.read_text())
                if "mac" in cfg and isinstance(cfg["mac"], dict):
                    cfg = cfg["mac"]
                server_url = cfg.get("server_url", server_url)
            except Exception:
                pass
        if core:
            try:
                adapter = core._sm.adapter()
                if adapter:
                    server_url = adapter._server_url
            except Exception:
                pass
        checks.append(_check_xcode_first_launch())
        checks.append(_check_appium_server(server_url))
        checks.append(_check_mac2_driver())

    if scope == "all":
        checks.append(_check_config())

    any_fail = any(c["status"] == "fail" for c in checks)
    all_pass = all(c["status"] == "pass" for c in checks)
    if any_fail:
        return error_response("doctor", ErrorCode.BACKEND_UNAVAILABLE,
                              "One or more checks failed.",
                              details={"checks": checks, "all_pass": False})
    return success_response("doctor", data={"checks": checks, "all_pass": all_pass})
