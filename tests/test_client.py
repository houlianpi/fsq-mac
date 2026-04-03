# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for client.py — DaemonClient, connection pooling, retry logic."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch, PropertyMock

import httpx
import pytest

from fsq_mac.client import DaemonClient, PID_FILE, PORT_FILE, DEFAULT_PORT


class TestReadPortPid:
    def test_read_port(self, tmp_path, monkeypatch):
        port_file = tmp_path / "daemon.port"
        port_file.write_text("12345")
        monkeypatch.setattr("fsq_mac.client.PORT_FILE", port_file)
        client = DaemonClient()
        assert client._read_port() == 12345

    def test_read_port_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.client.PORT_FILE", tmp_path / "nofile")
        client = DaemonClient()
        assert client._read_port() is None

    def test_read_pid(self, tmp_path, monkeypatch):
        pid_file = tmp_path / "daemon.pid"
        pid_file.write_text("99999")
        monkeypatch.setattr("fsq_mac.client.PID_FILE", pid_file)
        client = DaemonClient()
        assert client._read_pid() == 99999

    def test_read_pid_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.client.PID_FILE", tmp_path / "nofile")
        client = DaemonClient()
        assert client._read_pid() is None


class TestIsAlive:
    def test_no_pid(self, monkeypatch):
        client = DaemonClient()
        monkeypatch.setattr(client, "_read_pid", lambda: None)
        assert client._is_alive() is False

    def test_pid_not_running(self, monkeypatch):
        client = DaemonClient()
        monkeypatch.setattr(client, "_read_pid", lambda: 999999999)
        assert client._is_alive() is False


class TestCallSuccess:
    def test_call_success(self, monkeypatch):
        client = DaemonClient()
        client._base_url = "http://127.0.0.1:19444"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "command": "session.start"}

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        client._client = mock_http_client

        result = client.call("session", "start")
        assert result["ok"] is True
        mock_http_client.post.assert_called_once()

    def test_call_500(self, monkeypatch):
        client = DaemonClient()
        client._base_url = "http://127.0.0.1:19444"

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        client._client = mock_http_client

        result = client.call("session", "start")
        assert result["ok"] is False
        assert result["error"]["code"] == "BACKEND_UNAVAILABLE"

    def test_call_retry_on_connect_error(self, monkeypatch):
        client = DaemonClient()
        client._base_url = "http://127.0.0.1:19444"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("refused")
            return mock_response

        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = mock_post
        client._client = mock_http_client

        # _ensure_daemon should succeed on retry
        monkeypatch.setattr(client, "_ensure_daemon", lambda: "http://127.0.0.1:19444")

        # After the ConnectError, client._client is set to None, so _get_client
        # creates a new one. We need to patch _get_client to return our mock.
        original_get = client._get_client

        def patched_get():
            client._client = mock_http_client
            return mock_http_client

        monkeypatch.setattr(client, "_get_client", patched_get)

        result = client.call("session", "start")
        assert result["ok"] is True

    def test_call_generic_exception(self, monkeypatch):
        client = DaemonClient()
        client._base_url = "http://127.0.0.1:19444"

        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = ValueError("Unexpected")
        client._client = mock_http_client

        result = client.call("session", "start")
        assert result["ok"] is False
        assert result["error"]["code"] == "INTERNAL_ERROR"


class TestStopDaemon:
    def test_stop_daemon_with_pid(self, tmp_path, monkeypatch):
        pid_file = tmp_path / "daemon.pid"
        pid_file.write_text(str(os.getpid()))
        monkeypatch.setattr("fsq_mac.client.PID_FILE", pid_file)

        client = DaemonClient()
        client._base_url = "http://something"

        with patch("os.kill") as mock_kill:
            client.stop_daemon()
            mock_kill.assert_called_once_with(os.getpid(), 15)
        assert client._base_url is None

    def test_stop_daemon_no_pid(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.client.PID_FILE", tmp_path / "nofile")
        client = DaemonClient()
        client._base_url = "http://something"
        client.stop_daemon()
        assert client._base_url is None


class TestConnectionPool:
    def test_get_client_creates_once(self):
        client = DaemonClient()
        c1 = client._get_client()
        c2 = client._get_client()
        assert c1 is c2
        c1.close()

    def test_get_client_with_verbosity(self):
        client = DaemonClient(verbosity="debug")
        c = client._get_client()
        assert c.headers.get("x-verbosity") == "debug"
        c.close()

    def test_client_reset_on_retry(self):
        client = DaemonClient()
        c1 = client._get_client()
        client._client = None  # simulate retry reset
        c2 = client._get_client()
        assert c1 is not c2
        c1.close()
        c2.close()


class TestEnsureDaemon:
    def test_returns_cached_base_url(self):
        client = DaemonClient()
        client._base_url = "http://127.0.0.1:12345"
        assert client._ensure_daemon() == "http://127.0.0.1:12345"

    def test_alive_daemon_sets_base_url(self, monkeypatch):
        client = DaemonClient()
        monkeypatch.setattr(client, "_is_alive", lambda: True)
        monkeypatch.setattr(client, "_read_port", lambda: 19444)
        url = client._ensure_daemon()
        assert url == "http://127.0.0.1:19444"
        assert client._base_url == "http://127.0.0.1:19444"

    def test_dead_daemon_starts_new(self, monkeypatch):
        client = DaemonClient()
        monkeypatch.setattr(client, "_is_alive", lambda: False)
        monkeypatch.setattr(client, "_start_daemon", lambda: 19444)
        url = client._ensure_daemon()
        assert url == "http://127.0.0.1:19444"

    def test_alive_daemon_no_port(self, monkeypatch):
        client = DaemonClient()
        monkeypatch.setattr(client, "_is_alive", lambda: True)
        monkeypatch.setattr(client, "_read_port", lambda: None)
        url = client._ensure_daemon()
        assert url == f"http://127.0.0.1:{DEFAULT_PORT}"


class TestCallRetryPaths:
    def test_retry_500_on_second_attempt(self, monkeypatch):
        client = DaemonClient()
        client._base_url = "http://127.0.0.1:19444"

        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("refused")
            return mock_response_500

        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = mock_post
        client._client = mock_http_client

        monkeypatch.setattr(client, "_ensure_daemon", lambda: "http://127.0.0.1:19444")

        def patched_get():
            client._client = mock_http_client
            return mock_http_client

        monkeypatch.setattr(client, "_get_client", patched_get)

        result = client.call("session", "start")
        assert result["ok"] is False
        assert result["error"]["code"] == "BACKEND_UNAVAILABLE"

    def test_retry_total_failure(self, monkeypatch):
        client = DaemonClient()
        client._base_url = "http://127.0.0.1:19444"

        # First call raises ConnectError, retry also raises ConnectError
        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = httpx.ConnectError("refused")
        client._client = mock_http_client

        monkeypatch.setattr(client, "_ensure_daemon", lambda: "http://127.0.0.1:19444")

        # _get_client returns a client whose post also fails
        def patched_get():
            mock2 = MagicMock()
            mock2.post.side_effect = Exception("still broken")
            client._client = mock2
            return mock2

        monkeypatch.setattr(client, "_get_client", patched_get)

        result = client.call("session", "start")
        assert result["ok"] is False
        # patched_get runs on first call too, so generic Exception hits outer handler
        assert result["error"]["retryable"] is False
