"""Proxy package so that `backend.core` maps to the real `core` app."""
import sys
from importlib import import_module

module = import_module("core")
sys.modules[__name__] = module

