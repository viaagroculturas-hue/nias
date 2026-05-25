"""Compatibility wrapper.
Runtime imports this only when NIAS_AUTONOMOUS_MODE=1.
The implementation lives in scripts/autonomous_system.py after repository organization.
"""
from scripts.autonomous_system import *  # noqa: F401,F403
