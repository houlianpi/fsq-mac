# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for doctor.py — environment diagnostics."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from fsq_mac.doctor import (
    _check_accessibility, _check_appium_server, _check_mac2_driver,
    _check_config, _check_xcode_first_launch, run_checks,
)


class TestCheckAccessibility:
    def test_pass(self):
        completed = MagicMock()
        completed.returncode = 0
        with patch("subprocess.run", return_value=completed):
            result = _check_accessibility()
        assert result["status"] == "pass"

    def test_fail(self):
        completed = MagicMock()
        completed.returncode = 1
        with patch("subprocess.run", return_value=completed):
            result = _check_accessibility()
        assert result["status"] == "fail"
        assert "fix" in result

    def test_exception(self):
        with patch("subprocess.run", side_effect=Exception("boom")):
            result = _check_accessibility()
        assert result["status"] == "fail"


class TestCheckAppiumServer:
    def test_pass(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.get", return_value=mock_resp):
            result = _check_appium_server()
        assert result["status"] == "pass"

    def test_fail_non_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.get", return_value=mock_resp):
            result = _check_appium_server()
        assert result["status"] == "fail"

    def test_fail_unreachable(self):
        with patch("httpx.get", side_effect=Exception("unreachable")):
            result = _check_appium_server()
        assert result["status"] == "fail"


class TestCheckMac2Driver:
    def test_pass(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = json.dumps({"mac2": {"version": "1.0"}})
        with patch("subprocess.run", return_value=completed):
            result = _check_mac2_driver()
        assert result["status"] == "pass"

    def test_fail_not_found(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = json.dumps({"safari": {}})
        with patch("subprocess.run", return_value=completed):
            result = _check_mac2_driver()
        assert result["status"] == "fail"

    def test_fail_no_appium(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _check_mac2_driver()
        assert result["status"] == "fail"
        assert "npm install" in result.get("fix", "")

    def test_fail_exception(self):
        with patch("subprocess.run", side_effect=Exception("boom")):
            result = _check_mac2_driver()
        assert result["status"] == "fail"


class TestCheckConfig:
    def test_pass(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.doctor.STATE_DIR", tmp_path)
        (tmp_path / "config.json").write_text("{}")
        result = _check_config()
        assert result["status"] == "pass"

    def test_warn(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.doctor.STATE_DIR", tmp_path)
        result = _check_config()
        assert result["status"] == "warn"


class TestCheckXcodeFirstLaunch:
    def test_pass(self):
        completed = MagicMock()
        completed.returncode = 0
        with patch("subprocess.run", return_value=completed):
            result = _check_xcode_first_launch()
        assert result["status"] == "pass"

    def test_fail(self):
        completed = MagicMock()
        completed.returncode = 1
        with patch("subprocess.run", return_value=completed):
            result = _check_xcode_first_launch()
        assert result["status"] == "fail"

    def test_no_xcode(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _check_xcode_first_launch()
        assert result["status"] == "fail"
        assert "xcode-select" in result.get("fix", "")

    def test_exception(self):
        with patch("subprocess.run", side_effect=Exception("err")):
            result = _check_xcode_first_launch()
        assert result["status"] == "fail"


class TestRunChecks:
    def test_all_pass(self):
        with patch("fsq_mac.doctor._check_accessibility", return_value={"name": "acc", "status": "pass"}), \
             patch("fsq_mac.doctor._check_xcode_first_launch", return_value={"name": "xc", "status": "pass"}), \
             patch("fsq_mac.doctor._check_appium_server", return_value={"name": "srv", "status": "pass"}), \
             patch("fsq_mac.doctor._check_mac2_driver", return_value={"name": "drv", "status": "pass"}), \
             patch("fsq_mac.doctor._check_config", return_value={"name": "cfg", "status": "pass"}):
            resp = run_checks(scope="all")
        assert resp.ok is True
        assert resp.data["all_pass"] is True

    def test_any_fail(self):
        with patch("fsq_mac.doctor._check_accessibility", return_value={"name": "acc", "status": "fail"}), \
             patch("fsq_mac.doctor._check_xcode_first_launch", return_value={"name": "xc", "status": "pass"}), \
             patch("fsq_mac.doctor._check_appium_server", return_value={"name": "srv", "status": "pass"}), \
             patch("fsq_mac.doctor._check_mac2_driver", return_value={"name": "drv", "status": "pass"}), \
             patch("fsq_mac.doctor._check_config", return_value={"name": "cfg", "status": "pass"}):
            resp = run_checks(scope="all")
        assert resp.ok is False

    def test_scope_permissions(self):
        with patch("fsq_mac.doctor._check_accessibility", return_value={"name": "acc", "status": "pass"}) as mock_acc:
            resp = run_checks(scope="permissions")
        assert resp.ok is True
        mock_acc.assert_called_once()

    def test_scope_backend(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.doctor.STATE_DIR", tmp_path)
        with patch("fsq_mac.doctor._check_xcode_first_launch", return_value={"name": "xc", "status": "pass"}), \
             patch("fsq_mac.doctor._check_appium_server", return_value={"name": "srv", "status": "pass"}), \
             patch("fsq_mac.doctor._check_mac2_driver", return_value={"name": "drv", "status": "pass"}):
            resp = run_checks(scope="backend")
        assert resp.ok is True

    def test_scope_backend_with_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fsq_mac.doctor.STATE_DIR", tmp_path)
        (tmp_path / "config.json").write_text(
            json.dumps({"mac": {"server_url": "http://custom:9999"}})
        )
        with patch("fsq_mac.doctor._check_xcode_first_launch", return_value={"name": "xc", "status": "pass"}), \
             patch("fsq_mac.doctor._check_appium_server", return_value={"name": "srv", "status": "pass"}) as mock_srv, \
             patch("fsq_mac.doctor._check_mac2_driver", return_value={"name": "drv", "status": "pass"}):
            resp = run_checks(scope="backend")
        mock_srv.assert_called_once_with("http://custom:9999")

    def test_warn_still_passes(self):
        with patch("fsq_mac.doctor._check_accessibility", return_value={"name": "acc", "status": "warn"}), \
             patch("fsq_mac.doctor._check_xcode_first_launch", return_value={"name": "xc", "status": "pass"}), \
             patch("fsq_mac.doctor._check_appium_server", return_value={"name": "srv", "status": "pass"}), \
             patch("fsq_mac.doctor._check_mac2_driver", return_value={"name": "drv", "status": "pass"}), \
             patch("fsq_mac.doctor._check_config", return_value={"name": "cfg", "status": "warn"}):
            resp = run_checks(scope="all")
        assert resp.ok is True
        assert resp.data["all_pass"] is False
