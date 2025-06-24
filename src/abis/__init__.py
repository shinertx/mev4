"""Shim module so code/tests can import `src.abis.*`.

It re-exports ABI constants from the real modules in the top-level `abis/` directory
without duplicating data or changing project layout.
"""

from importlib import import_module
from types import ModuleType
from typing import Dict
import sys
import types

# Map of attribute names we want to expose -> (module_path, attr_name)
_ABI_EXPORTS: Dict[str, tuple[str, str]] = {
    "ERC20_ABI": ("abis.erc20", "ERC20_ABI"),
    "UNISWAP_V2_ROUTER_ABI": ("abis.uniswap_v2", "UNISWAP_V2_ROUTER_ABI"),
}

# Ensure this package object is registered in sys.modules
_current_module: ModuleType = sys.modules.setdefault(__name__, sys.modules.get(__name__, types.ModuleType(__name__)))

for public_name, (mod_path, attr_name) in _ABI_EXPORTS.items():
    try:
        mod = import_module(mod_path)
        setattr(_current_module, public_name, getattr(mod, attr_name))
        # Also expose a proxy sub-module so 'import src.abis.<name>' works
        proxy_name = f"{__name__}.{mod_path.split('.')[-1]}"
        proxy_mod = types.ModuleType(proxy_name)
        setattr(proxy_mod, attr_name, getattr(mod, attr_name))
        sys.modules[proxy_name] = proxy_mod
    except (ModuleNotFoundError, AttributeError):
        # Underlying ABI module missing – expose empty placeholder to keep imports working
        setattr(_current_module, public_name, [])
        proxy_name = f"{__name__}.{mod_path.split('.')[-1]}"
        proxy_mod = types.ModuleType(proxy_name)
        setattr(proxy_mod, attr_name, [])
        sys.modules[proxy_name] = proxy_mod

__all__ = list(_ABI_EXPORTS.keys()) 