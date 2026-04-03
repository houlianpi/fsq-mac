# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for cli.py — parser, global flags, exit codes."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from fsq_mac.cli import _build_parser, _run, main


class TestParser:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "fsq-mac" in captured.out

    def test_verbose_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--verbose", "session", "start"])
        assert args.verbose is True
        assert args.debug is False

    def test_debug_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--debug", "session", "start"])
        assert args.debug is True

    def test_session_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--session", "s1", "session", "get"])
        assert args.session == "s1"

    def test_strategy_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--strategy", "xpath", "element", "find", "btn"])
        assert args.strategy == "xpath"

    def test_timeout_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--timeout", "5000", "session", "start"])
        assert args.timeout == 5000

    def test_pretty_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--pretty", "session", "start"])
        assert args.pretty is True

    def test_allow_dangerous_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--allow-dangerous", "app", "terminate", "com.test"])
        assert args.allow_dangerous is True

    def test_no_domain_exits(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1


class TestParserDomains:
    def test_session_start(self):
        parser = _build_parser()
        args = parser.parse_args(["session", "start"])
        assert args.domain == "session"
        assert args.action == "start"

    def test_app_launch(self):
        parser = _build_parser()
        args = parser.parse_args(["app", "launch", "com.apple.calculator"])
        assert args.domain == "app"
        assert args.action == "launch"
        assert args.bundle_id == "com.apple.calculator"

    def test_element_find(self):
        parser = _build_parser()
        args = parser.parse_args(["element", "find", "btn", "--first-match"])
        assert args.action == "find"
        assert args.locator == "btn"
        assert args.first_match is True

    def test_element_click(self):
        parser = _build_parser()
        args = parser.parse_args(["element", "click", "e0"])
        assert args.ref == "e0"

    def test_element_type(self):
        parser = _build_parser()
        args = parser.parse_args(["element", "type", "e0", "hello"])
        assert args.ref == "e0"
        assert args.text == "hello"

    def test_element_scroll(self):
        parser = _build_parser()
        args = parser.parse_args(["element", "scroll", "e0", "up"])
        assert args.direction == "up"

    def test_element_drag(self):
        parser = _build_parser()
        args = parser.parse_args(["element", "drag", "e0", "e1"])
        assert args.source == "e0"
        assert args.target == "e1"

    def test_input_key(self):
        parser = _build_parser()
        args = parser.parse_args(["input", "key", "return"])
        assert args.key == "return"

    def test_input_hotkey(self):
        parser = _build_parser()
        args = parser.parse_args(["input", "hotkey", "command+c"])
        assert args.combo == "command+c"

    def test_input_text(self):
        parser = _build_parser()
        args = parser.parse_args(["input", "text", "hello"])
        assert args.text == "hello"

    def test_capture_screenshot(self):
        parser = _build_parser()
        args = parser.parse_args(["capture", "screenshot", "/tmp/s.png"])
        assert args.path == "/tmp/s.png"

    def test_capture_screenshot_element(self):
        parser = _build_parser()
        args = parser.parse_args(["capture", "screenshot", "--element", "e0"])
        assert args.element == "e0"

    def test_capture_screenshot_rect(self):
        parser = _build_parser()
        args = parser.parse_args(["capture", "screenshot", "--rect", "0,0,100,100"])
        assert args.rect == "0,0,100,100"

    def test_wait_element(self):
        parser = _build_parser()
        args = parser.parse_args(["wait", "element", "btn"])
        assert args.locator == "btn"

    def test_wait_window(self):
        parser = _build_parser()
        args = parser.parse_args(["wait", "window", "Test"])
        assert args.title == "Test"

    def test_wait_app(self):
        parser = _build_parser()
        args = parser.parse_args(["wait", "app", "com.test"])
        assert args.bundle_id == "com.test"

    def test_window_focus(self):
        parser = _build_parser()
        args = parser.parse_args(["window", "focus", "0"])
        assert args.index == 0


class TestRun:
    def _make_args(self, argv):
        parser = _build_parser()
        args = parser.parse_args(argv)
        args.verbose = False
        args.debug = False
        return args

    def test_run_maps_session_start(self):
        args = self._make_args(["session", "start"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            result = _run(args)
        assert result["ok"] is True
        mock_instance.call.assert_called_once()
        call_args = mock_instance.call.call_args
        assert call_args[0] == ("session", "start")

    def test_run_maps_app_launch(self):
        args = self._make_args(["app", "launch", "com.test"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            result = _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["bundle_id"] == "com.test"

    def test_run_maps_element_find(self):
        args = self._make_args(["element", "find", "btn", "--first-match"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            result = _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["locator"] == "btn"
        assert call_kwargs["first_match"] is True

    def test_run_maps_element_click(self):
        args = self._make_args(["element", "click", "e0"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["ref"] == "e0"

    def test_run_maps_element_type(self):
        args = self._make_args(["element", "type", "e0", "hello"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["ref"] == "e0"
        assert call_kwargs["text"] == "hello"

    def test_run_maps_element_scroll(self):
        args = self._make_args(["element", "scroll", "e0", "up"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["ref"] == "e0"
        assert call_kwargs["direction"] == "up"

    def test_run_maps_element_drag(self):
        args = self._make_args(["element", "drag", "e0", "e1"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["ref"] == "e0"
        assert call_kwargs["target"] == "e1"

    def test_run_maps_input_key(self):
        args = self._make_args(["input", "key", "return"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["key"] == "return"

    def test_run_maps_input_hotkey(self):
        args = self._make_args(["input", "hotkey", "command+c"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["combo"] == "command+c"

    def test_run_maps_input_text(self):
        args = self._make_args(["input", "text", "hello"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["text"] == "hello"

    def test_run_maps_capture_screenshot(self):
        args = self._make_args(["capture", "screenshot", "/tmp/s.png"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["path"] == "/tmp/s.png"

    def test_run_maps_capture_screenshot_with_element(self):
        args = self._make_args(["capture", "screenshot", "--element", "e0"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["ref"] == "e0"

    def test_run_maps_capture_screenshot_with_rect(self):
        args = self._make_args(["capture", "screenshot", "--rect", "0,0,100,100"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["rect"] == "0,0,100,100"

    def test_run_maps_wait_element(self):
        args = self._make_args(["wait", "element", "btn"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["locator"] == "btn"

    def test_run_maps_wait_window(self):
        args = self._make_args(["wait", "window", "Test"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["title"] == "Test"

    def test_run_maps_wait_app(self):
        args = self._make_args(["wait", "app", "com.test"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["bundle_id"] == "com.test"

    def test_run_maps_window_focus(self):
        args = self._make_args(["window", "focus", "0"])
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        call_kwargs = mock_instance.call.call_args[1]
        assert call_kwargs["index"] == 0

    def test_run_verbosity_debug(self):
        args = self._make_args(["session", "start"])
        args.debug = True
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        MockClient.assert_called_once()
        assert MockClient.call_args[1]["verbosity"] == "debug"

    def test_run_verbosity_verbose(self):
        args = self._make_args(["session", "start"])
        args.verbose = True
        with patch("fsq_mac.cli.DaemonClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.call.return_value = {"ok": True}
            MockClient.return_value = mock_instance
            _run(args)
        assert MockClient.call_args[1]["verbosity"] == "verbose"


class TestMainExitCodes:
    def test_success_exit_0(self, capsys):
        with patch("fsq_mac.cli._run", return_value={"ok": True, "command": "test"}):
            main(["session", "start"])

    def test_error_exit_1(self, capsys):
        with patch("fsq_mac.cli._run", return_value={"ok": False, "command": "test", "error": {"code": "ERR", "message": "fail"}}):
            with pytest.raises(SystemExit) as exc_info:
                main(["session", "start"])
            assert exc_info.value.code == 1
