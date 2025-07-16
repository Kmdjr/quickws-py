import importlib.util
import pkgutil
import importlib
import sys
from typing import List
from pathlib import Path
from typing import Union, Callable, Optional

def _plugin_list_checker(plugindirs: Union[str, List[str]]) -> List[Path]:
    """
    Normalize plugindirs into a list of existing Path objects.
    """
    if isinstance(plugindirs, str):
        plugindirs = [plugindirs]
    if not isinstance(plugindirs, list):
        print("Invalid type for plugindirs. Must be str or list[str].")
        return []

    dirs: List[Path] = []
    missing: List[str] = []
    for d in plugindirs:
        p = Path(d)
        if p.is_dir():
            dirs.append(p)
        else:
            missing.append(d)

    if dirs:
        names = ", ".join(str(d) for d in dirs)
        print(f"Found plugin directories: {names}")
    if missing:
        names = ", ".join(missing)
        print(f"Warning: these paths do not exist or are not dirs: {names}")

    return [dirs,missing]

class PluginManager:
    def __init__(self,plugindirs:list[str]):
        """
        plugindir: the path to your plugins folder. Uses pathlib.
        """
        dir_info = _plugin_list_checker(plugindirs=plugindirs)
        self.dirs = dir_info[0]
        self.failed = dir_info[1]
        self._loaded = []
    
    def discover(self) -> List[Path]:
        plugins:List[Path] = []
        for d in self.dirs:
            for p in d.glob("*.py"):
                if p.name == "__init__.py":
                    continue
                plugins.append(p)
        return plugins
    
    def load(self, server) -> None:
        loaded_plugins: List[str] = []
        failed_plugins: List[str] = []

        for path in self.discover():
            module_name = f"plugins.{path.stem}"
            if module_name in self._loaded:
                continue

            spec = importlib.util.spec_from_file_location(module_name, str(path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod
                try:
                    spec.loader.exec_module(mod)
                except Exception as e:
                    print(f"[plugin] Error importing {path.name}: {e}")
                    failed_plugins.append(path.name)
                    continue

                setup = getattr(mod, "setup", None)
                if callable(setup):
                    try:
                        setup(server)
                        print(f"[plugin] Loaded {path.name} successfully")
                        self._loaded.append(module_name)
                        loaded_plugins.append(path.name)
                    except Exception as e:
                        print(f"[plugin] Error running setup() in {path.name}: {e}")
                        failed_plugins.append(path.name)
                else:
                    print(f"[plugin] {path.name} has no setup(server), skipping.")
                    failed_plugins.append(path.name)
            else:
                print(f"[plugin] Could not load spec for {path.name}")
                failed_plugins.append(path.name)

        # Print summary
        print(f"\n[plugin] Plugins Loaded Successfully ({len(loaded_plugins)}): {', '.join(loaded_plugins) or 'None'}")
        print(f"[plugin] Plugins Failed ({len(failed_plugins)}): {', '.join(failed_plugins) or 'None'}")
