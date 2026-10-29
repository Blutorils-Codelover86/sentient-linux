"""
Performance benchmark tests for Sentient Linux on Omarchy / Hyprland.
Measures real latency and memory metrics.
"""

from __future__ import annotations
import os
import resource
import time
import pytest

from sentient_linux.perception.hyprland import HyprlandInspector
from sentient_linux.perception.screenshots import ScreenshotEngine
from sentient_linux.inference.ollama import OllamaClient
from sentient_linux.computer_use.mock_client import MockMCPClient
from sentient_linux.computer_use.mcp_client import LiveMCPClient
from sentient_linux.computer_use.action_schema import ActionType, ProposedAction


def test_benchmark_window_inspection():
    inspector = HyprlandInspector()
    if not inspector.is_available():
        pytest.skip("hyprctl not available in test environment")

    # Measure activewindow query latency over 5 iterations
    latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        _ = inspector.get_focused_window()
        latencies.append((time.perf_counter() - t0) * 1000.0)

    avg_latency = sum(latencies) / len(latencies)
    print(f"\n[BENCHMARK] Window Inspection Latency: avg={avg_latency:.2f}ms, min={min(latencies):.2f}ms, max={max(latencies):.2f}ms")
    # Hyprland IPC is expected to complete comfortably under 100ms
    assert avg_latency < 100.0


def test_benchmark_screenshot_capture():
    engine = ScreenshotEngine()
    if not engine.is_available():
        pytest.skip("grim not available in test environment")

    latencies = []
    sizes = []
    for _ in range(3):
        res = engine.capture()
        latencies.append(res.latency_ms)
        sizes.append(res.size_bytes)
        res.cleanup()

    avg_latency = sum(latencies) / len(latencies)
    avg_size_kb = (sum(sizes) / len(sizes)) / 1024.0
    print(f"\n[BENCHMARK] Screenshot Capture (grim): avg={avg_latency:.2f}ms, avg_size={avg_size_kb:.1f}KB")
    assert avg_latency < 3000.0


def test_benchmark_mcp_mock_overhead():
    mock = MockMCPClient()
    action = ProposedAction(action_type=ActionType.LIST_WINDOWS)

    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = mock.execute(action)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    avg_overhead = sum(latencies) / len(latencies)
    print(f"\n[BENCHMARK] MCP Mock Request Overhead: avg={avg_overhead:.4f}ms")
    assert avg_overhead < 1.0


def test_benchmark_live_mcp_overhead():
    client = LiveMCPClient()
    if not client.is_available():
        pytest.skip("computer-use-linux binary not found")

    client.start()
    latencies = []
    try:
        for _ in range(3):
            t0 = time.perf_counter()
            _ = client.call_tool("list_windows", {})
            latencies.append((time.perf_counter() - t0) * 1000.0)
    finally:
        client.stop()

    avg_latency = sum(latencies) / len(latencies)
    print(f"\n[BENCHMARK] Live MCP JSON-RPC Latency (list_windows): avg={avg_latency:.2f}ms")
    assert avg_latency < 3000.0


def test_benchmark_memory_consumption():
    # Measure Resident Set Size (RSS) in KB
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss_mb = usage.ru_maxrss / 1024.0  # Linux ru_maxrss is in KiB
    print(f"\n[BENCHMARK] Sentient Linux Process Peak RSS Memory: {rss_mb:.2f} MB")
    # Base Python process tree under pytest should remain under 500 MB
    assert rss_mb < 500.0
