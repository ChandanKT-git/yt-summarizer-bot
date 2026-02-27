"""Pytest configuration — adds project root to sys.path."""
import sys
import os

# Ensure the project root is in sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
