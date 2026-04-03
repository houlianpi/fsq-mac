# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for configurable delays in the adapter."""

from __future__ import annotations

from fsq_mac.adapters.appium_mac2 import AppiumMac2Adapter


class TestAdapterDelayDefaults:
    def test_default_post_action(self):
        adapter = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        assert adapter._delay_post_action == 1.0

    def test_default_pre_input(self):
        adapter = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        assert adapter._delay_pre_input == 0.5

    def test_default_double_click_gap(self):
        adapter = AppiumMac2Adapter({"server_url": "http://127.0.0.1:4723"})
        assert adapter._delay_double_click_gap == 0.1


class TestAdapterDelayOverrides:
    def test_override_post_action(self):
        adapter = AppiumMac2Adapter({
            "server_url": "http://127.0.0.1:4723",
            "delay_post_action": 0.5,
        })
        assert adapter._delay_post_action == 0.5

    def test_override_pre_input(self):
        adapter = AppiumMac2Adapter({
            "server_url": "http://127.0.0.1:4723",
            "delay_pre_input": 0.2,
        })
        assert adapter._delay_pre_input == 0.2

    def test_override_double_click_gap(self):
        adapter = AppiumMac2Adapter({
            "server_url": "http://127.0.0.1:4723",
            "delay_double_click_gap": 0.05,
        })
        assert adapter._delay_double_click_gap == 0.05

    def test_zero_delays(self):
        adapter = AppiumMac2Adapter({
            "server_url": "http://127.0.0.1:4723",
            "delay_post_action": 0,
            "delay_pre_input": 0,
            "delay_double_click_gap": 0,
        })
        assert adapter._delay_post_action == 0
        assert adapter._delay_pre_input == 0
        assert adapter._delay_double_click_gap == 0
