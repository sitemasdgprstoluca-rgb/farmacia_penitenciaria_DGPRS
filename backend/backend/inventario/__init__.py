"""Proxy package so that `backend.inventario` maps to the real `inventario` app."""
import sys
from importlib import import_module

module = import_module("inventario")
sys.modules[__name__] = module

