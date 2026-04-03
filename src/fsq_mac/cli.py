# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""mac — CLI entry point.

Usage:  mac <domain> <action> [args] [options]
"""

from __future__ import annotations

import argparse
import sys

from fsq_mac import __version__
from fsq_mac.client import DaemonClient
from fsq_mac.formatters import output


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mac",
        description="Agent-first macOS automation CLI",
    )
    p.add_argument("--version", action="version", version=f"fsq-mac {__version__}")
    p.add_argument("--session", default=None, help="Session ID (default: most recent)")
    p.add_argument("--strategy", default="accessibility_id",
                   help="Element locator strategy (default: accessibility_id)")
    p.add_argument("--timeout", type=int, default=120000, help="Timeout in ms (default: 120000)")
    p.add_argument("--pretty", action="store_true", help="Human-friendly output")
    p.add_argument("--allow-dangerous", action="store_true", help="Allow dangerous operations")

    sub = p.add_subparsers(dest="domain", help="Command domain")

    # -- session --
    session = sub.add_parser("session", help="Session management")
    sa = session.add_subparsers(dest="action")
    sa.add_parser("start", help="Start a new session")
    sa.add_parser("get", help="Get current session info")
    sa.add_parser("list", help="List all sessions")
    sa.add_parser("end", help="End current session")

    # -- app --
    app = sub.add_parser("app", help="Application management")
    aa = app.add_subparsers(dest="action")
    launch = aa.add_parser("launch", help="Launch an application")
    launch.add_argument("bundle_id", help="Bundle ID (e.g. com.apple.calculator)")
    activate = aa.add_parser("activate", help="Activate a running application")
    activate.add_argument("bundle_id", help="Bundle ID")
    aa.add_parser("list", help="List running applications")
    aa.add_parser("current", help="Get frontmost application")
    term = aa.add_parser("terminate", help="Terminate an application")
    term.add_argument("bundle_id", help="Bundle ID")

    # -- window --
    win = sub.add_parser("window", help="Window management")
    wa = win.add_subparsers(dest="action")
    wa.add_parser("current", help="Get frontmost window info")
    wa.add_parser("list", help="List windows")
    focus = wa.add_parser("focus", help="Focus a window")
    focus.add_argument("index", type=int, help="Window index")

    # -- element --
    elem = sub.add_parser("element", help="Element operations")
    ea = elem.add_subparsers(dest="action")
    ea.add_parser("inspect", help="Inspect current UI elements")
    find = ea.add_parser("find", help="Find elements by locator")
    find.add_argument("locator", help="Locator value")
    find.add_argument("--first-match", action="store_true", help="Return first match only")
    click = ea.add_parser("click", help="Click an element")
    click.add_argument("ref", help="Element reference (e.g. e5 or locator)")
    rclick = ea.add_parser("right-click", help="Right-click an element")
    rclick.add_argument("ref", help="Element reference")
    dclick = ea.add_parser("double-click", help="Double-click an element")
    dclick.add_argument("ref", help="Element reference")
    etype = ea.add_parser("type", help="Type text into an element")
    etype.add_argument("ref", help="Element reference")
    etype.add_argument("text", help="Text to type")
    scroll = ea.add_parser("scroll", help="Scroll an element")
    scroll.add_argument("ref", help="Element reference")
    scroll.add_argument("direction", nargs="?", default="down",
                        choices=["up", "down", "left", "right"], help="Scroll direction")
    ehover = ea.add_parser("hover", help="Hover over an element")
    ehover.add_argument("ref", help="Element reference")
    drag = ea.add_parser("drag", help="Drag from source to target")
    drag.add_argument("source", help="Source element reference")
    drag.add_argument("target", help="Target element reference")

    # -- input --
    inp = sub.add_parser("input", help="Direct input (no element)")
    ia = inp.add_subparsers(dest="action")
    key = ia.add_parser("key", help="Press a single key")
    key.add_argument("key", help="Key name (e.g. return, space, tab)")
    hotkey = ia.add_parser("hotkey", help="Press a key combination")
    hotkey.add_argument("combo", help="Combo (e.g. command+c)")
    text = ia.add_parser("text", help="Type text to focused element")
    text.add_argument("text", help="Text to type")

    # -- capture --
    cap = sub.add_parser("capture", help="Capture screen or UI tree")
    ca = cap.add_subparsers(dest="action")
    ss = ca.add_parser("screenshot", help="Take a screenshot")
    ss.add_argument("path", nargs="?", default="./screenshot.png", help="Output file path")
    ss_group = ss.add_mutually_exclusive_group()
    ss_group.add_argument("--element", metavar="REF", help="Screenshot a specific element (e.g. e0)")
    ss_group.add_argument("--rect", metavar="x,y,w,h", help="Screenshot a region")
    ca.add_parser("ui-tree", help="Get UI element tree")

    # -- wait --
    wait = sub.add_parser("wait", help="Wait for conditions")
    wta = wait.add_subparsers(dest="action")
    we = wta.add_parser("element", help="Wait for element to appear")
    we.add_argument("locator", help="Locator value")
    ww = wta.add_parser("window", help="Wait for window to appear")
    ww.add_argument("title", help="Window title")
    wapp = wta.add_parser("app", help="Wait for application to start")
    wapp.add_argument("bundle_id", help="Bundle ID")

    # -- doctor --
    doc = sub.add_parser("doctor", help="Environment diagnostics")
    da = doc.add_subparsers(dest="action")
    da.add_parser("permissions", help="Check Accessibility permissions")
    da.add_parser("backend", help="Check Appium server and Mac2 driver")

    return p


def _run(args: argparse.Namespace) -> dict:
    """Translate parsed args into a daemon API call."""
    client = DaemonClient(timeout=max(args.timeout / 1000 + 10, 30))

    domain = args.domain
    action = getattr(args, "action", None) or "all"

    params: dict = {
        "session": args.session,
        "allow_dangerous": args.allow_dangerous,
    }

    # Map positional args to params based on domain/action
    if domain == "app" and action in ("launch", "activate", "terminate"):
        params["bundle_id"] = args.bundle_id

    elif domain == "element":
        params["strategy"] = args.strategy
        if action == "find":
            params["locator"] = args.locator
            params["first_match"] = args.first_match
        elif action in ("click", "right-click", "double-click", "hover"):
            params["ref"] = args.ref
        elif action == "type":
            params["ref"] = args.ref
            params["text"] = args.text
        elif action == "scroll":
            params["ref"] = args.ref
            params["direction"] = args.direction
        elif action == "drag":
            params["ref"] = args.source
            params["target"] = args.target

    elif domain == "input":
        if action == "key":
            params["key"] = args.key
        elif action == "hotkey":
            params["combo"] = args.combo
        elif action == "text":
            params["text"] = args.text

    elif domain == "capture":
        if action == "screenshot":
            params["path"] = args.path
            if getattr(args, "element", None):
                params["ref"] = args.element
            if getattr(args, "rect", None):
                params["rect"] = args.rect

    elif domain == "wait":
        params["strategy"] = args.strategy
        params["timeout"] = args.timeout
        if action == "element":
            params["locator"] = args.locator
        elif action == "window":
            params["title"] = args.title
        elif action == "app":
            params["bundle_id"] = args.bundle_id

    elif domain == "window" and action == "focus":
        params["index"] = args.index

    return client.call(domain, action, **params)


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args, remaining = parser.parse_known_args(argv)
    # Re-parse remaining args to pick up global options after subcommand
    if remaining:
        args, _ = parser.parse_known_args(remaining, args)

    if not args.domain:
        parser.print_help()
        sys.exit(1)

    if not getattr(args, "action", None) and args.domain != "doctor":
        # Show subcommand help
        parser.parse_args([args.domain, "--help"])
        return

    # doctor without action = run all checks
    if args.domain == "doctor" and not getattr(args, "action", None):
        args.action = "all"

    result = _run(args)
    print(output(result, pretty=args.pretty))

    if not result.get("ok", True):
        sys.exit(1)


if __name__ == "__main__":
    main()
