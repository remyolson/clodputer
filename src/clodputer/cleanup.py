# Copyright (c) 2025 Rémy Olson
"""
Utilities for cleaning up Claude Code processes and their children.

The tracer bullet only needs a pared-down version of the final cleanup strategy,
but the implementation already follows the structure described in the planning
documents: terminate the main process, walk the child tree, and perform a final
name-based sweep for stray MCP processes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Sequence

import psutil

logger = logging.getLogger(__name__)


@dataclass
class CleanupReport:
    """Summary of the cleanup operation."""

    terminated: List[int]
    killed: List[int]
    orphaned_mcps: List[int]

    @property
    def total(self) -> int:
        return len(self.terminated) + len(self.killed) + len(self.orphaned_mcps)


def _terminate_processes(processes: Sequence[psutil.Process]) -> List[int]:
    terminated: List[int] = []
    for proc in processes:
        try:
            proc.terminate()
            terminated.append(proc.pid)
        except psutil.NoSuchProcess:  # pragma: no cover - process already exited
            continue
        except psutil.Error as exc:  # pragma: no cover - unexpected psutil failure
            logger.warning("Failed to terminate process %s: %s", proc.pid, exc)
    return terminated


def _kill_processes(processes: Sequence[psutil.Process]) -> List[int]:
    killed: List[int] = []
    for proc in processes:
        try:
            proc.kill()
            killed.append(proc.pid)
        except psutil.NoSuchProcess:  # pragma: no cover
            continue
        except psutil.Error as exc:  # pragma: no cover
            logger.warning("Failed to kill process %s: %s", proc.pid, exc)
    return killed


def _find_orphaned_mcp_processes() -> Iterable[psutil.Process]:
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info.get("name")
        except (psutil.NoSuchProcess, psutil.AccessDenied):  # pragma: no cover
            continue
        if name and "mcp__" in name:
            yield proc


def cleanup_process_tree(root_pid: int, grace_period: float = 5.0) -> CleanupReport:
    """
    Terminate the Claude Code process tree and perform a final sweep for orphaned MCPs.

    Args:
        root_pid: PID of the main Claude Code process.
        grace_period: Seconds to wait after SIGTERM before issuing SIGKILL.

    Returns:
        CleanupReport summarising which processes were terminated.
    """
    root_proc: psutil.Process | None
    root_children: List[psutil.Process]
    try:
        root_proc = psutil.Process(root_pid)
    except psutil.NoSuchProcess:
        root_proc = None
        root_children = []
    else:
        root_children = root_proc.children(recursive=True)

    processes_to_handle: List[psutil.Process] = []
    if root_proc is not None:
        processes_to_handle.append(root_proc)
    processes_to_handle.extend(root_children)

    terminated = _terminate_processes(processes_to_handle)
    if processes_to_handle:
        # Give the processes a short grace period to exit cleanly.
        psutil.wait_procs(processes_to_handle, timeout=grace_period)

    alive_after_grace: List[psutil.Process] = []
    for proc in processes_to_handle:
        try:
            if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                alive_after_grace.append(proc)
        except (psutil.NoSuchProcess, psutil.Error):  # pragma: no cover
            continue
    killed = _kill_processes(alive_after_grace)

    orphaned_mcps = []
    for proc in _find_orphaned_mcp_processes():
        if proc.pid in terminated or proc.pid in killed:
            continue
        try:
            proc.kill()
            orphaned_mcps.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.Error):  # pragma: no cover
            continue

    if terminated or killed or orphaned_mcps:
        logger.info(
            "Cleanup complete (terminated=%s, killed=%s, orphaned=%s)",
            terminated,
            killed,
            orphaned_mcps,
        )
    else:
        logger.info("No processes required cleanup for pid=%s", root_pid)

    return CleanupReport(terminated=terminated, killed=killed, orphaned_mcps=orphaned_mcps)


__all__ = ["cleanup_process_tree", "CleanupReport"]
