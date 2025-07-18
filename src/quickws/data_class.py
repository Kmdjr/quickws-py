from .functional_utils.lists import in_lower_list, mergel, clean_values
from .functional_utils.types import multi_isinstance
from typing import Optional

class Data:
    """Flexible key-value store with protection and type locking."""

    def __init__(self, data_dictionary: dict, initial_typing:bool=False, **kwargs):
        """
        Initialize with:
          - `data_dictionary`: can be { key: val } or { key: {"value": val, "tags": [...]} }
          - `initial_typing`: whether to auto-lock types of kwargs
          - `**kwargs`: treated as protected (and, if initial_typing, type‑locked)
        """
        # 1) store originals
        self._og_list = data_dictionary
        self._og_protects = dict(kwargs)
        self._types = {}
        self._banned_attr = [
            "_og_list", "_og_protects", "_banned_attr", "_protected_attr", "_types"
        ]
        self._protected_attr = list(kwargs.keys())

        # 2) set protected kwargs as attributes
        for k, v in kwargs.items():
            if k not in self._banned_attr:
                setattr(self, k, v)

        # 3) process each entry in data_dictionary
        for key, raw in data_dictionary.items():
            if key in mergel(self._banned_attr, self._protected_attr):
                continue

            # if the value is a dict with a "value" and optional "tags"
            if isinstance(raw, dict) and "value" in raw:
                val = raw["value"]
                tags = raw.get("tags")
            else:
                val = raw
                tags = None

            # 3a) assign the actual value
            setattr(self, key, val)

            # 3b) if tags provided, apply them
            if isinstance(tags, list):
                for tag in tags:
                    if tag == "protected":
                        # mark this key protected
                        if key not in self._protected_attr:
                            self._protected_attr.append(key)
                    elif tag == "typed":
                        # lock its current type
                        self._types[key] = type(val)
                    elif tag == "kwarg":
                        # treat as if passed in via kwargs
                        self._og_protects[key] = raw
                        if key not in self._protected_attr:
                            self._protected_attr.append(key)

        # 4) optionally lock types of the original kwargs
        if initial_typing:
            for k, v in self._og_protects.items():
                self.add_typing(k, type(v))

    def hasprop(self, name: str, include_protected: bool = True) -> bool:
        """Return True if `name` exists. `include_protected` excludes protected attrs."""
        allowed = clean_values(
            self.__dict__.keys(),
            mergel(self._banned_attr, [] if include_protected else self._protected_attr)
        )
        return name in allowed

    def add_typing(self, property: str, type_lock: type = None) -> bool:
        """Set a type lock on `property`. `type_lock` (type) if None inferred. Returns True if applied, False otherwise."""
        if not multi_isinstance([property, type_lock], [str, (None, type)]):
            raise ValueError
        if property in self.__dict__.keys() and property not in self._banned_attr:
            type_lock = type_lock if type_lock else type(getattr(self, property))
            self._types[property] = type_lock
            if type(getattr(self, property)) != self._types[property]:
                setattr(self, property, None)
            return True
        return False
    
    def remove_typing(self, property: str) -> bool:
        """Remove type lock for `property`. Returns True if removed, False otherwise."""
        if not isinstance(property, str):
            raise ValueError(property)
        if property in self._types.keys():
            del self._types[property]
            return True
        return False
    
    def set_all_typings(self, protected_only: bool = False) -> int:
        """Lock types for all properties. `protected_only` (bool) if True only protected. Returns int count."""
        if not isinstance(protected_only, bool):
            raise ValueError(protected_only)
        count = 0
        prop_types = [(k, type(v)) for k, v in self.__dict__.items() if k not in self._banned_attr]
        for i in prop_types:
            if protected_only and self._procheck(i[0]):
                continue
            self.add_typing(i[0], i[1])
            count += 1
        return count

    def rem_all_typings(self, keep_protected: bool = True) -> int:
        """Unlock types for all. `keep_protected` (bool) if True keep protected. Returns int count."""
        if not isinstance(keep_protected, bool):
            raise ValueError(keep_protected)
        count = 0
        for key in list(self._types.keys()):
            if keep_protected and self._procheck(key):
                continue
            del self._types[key]
            count += 1
        return count

    def _gather_types(self):
        """Collect current types. No return."""
        for key, val in self.__dict__.items():
            if key in self._banned_attr:
                continue
            self._types[key] = type(val)

    def oset(self, attr: str, newval) -> bool:
        """Overwrite `attr` with `newval`. Returns True if existed, False otherwise."""
        if hasattr(self, attr):
            if self._check_for_type(attr,newval):
                setattr(self, attr, newval)
                return True
            self._typederr(attr,newval)
        return False

    def _del_attr(self,attr:str,override:bool=False):
        """Internal function to delete attribute and all references from types and protected."""
        if override:
            self.ounprotect(attr)
        else:
            self.unprotect(attr)
        self.remove_typing(attr)

    def erase(self,attr:str) -> bool:
        """Deletes `attr`. Returns True if exists, False otherwise."""
        if hasattr(self,attr) and not self._procheck(attr):
            self._del_attr(attr,False)
            delattr(self,attr)
            return True
        return False

    def oerase(self, attr: str) -> bool:
        """Delete any `attr` including protected ones. Returns True if existed, False otherwise."""
        if hasattr(self, attr):
            self._del_attr(attr,True)
            delattr(self, attr)
            return True
        return False

    def set(self, name: str, val) -> bool:
        """Set `name` to `val` unless protected. Returns True if set, False otherwise."""
        if not self._procheck(name):
            if self._check_for_type(name,val):
                setattr(self, name, val)
                return True
            self._typederr(name,val)
        return False
    
    def sets(self, **kwargs) -> int:
        """Set multiple `kwargs`. Returns int count of set."""
        count = 0
        for k, v in kwargs.items():
            if self.set(k, v):
                count += 1
        return count
    
    def osets(self, **kwargs) -> int:
        """Overwrite multiple `kwargs`. Returns int count of set."""
        count = 0
        for k, v in kwargs.items():
            if self.oset(k, v):
                count += 1
        return count

    def protect(self, name: str) -> bool:
        """Protect `name`. Returns True if newly protected, False otherwise."""
        if not self._procheck(name):
            self._protected_attr.append(name)
            return True
        return False

    def unprotect(self, name: str) -> bool:
        """Unprotect `name` if not from original kwargs. Returns True if unprotected, False otherwise."""
        if self._procheck(name) and not in_lower_list(name, self._og_protects.keys()):
            self._protected_attr = [
                attr for attr in self._protected_attr if attr.lower() != name.lower()
            ]
            return True
        return False

    def ounprotect(self, name: str) -> bool:
        """Force unprotect `name`. Returns True if unprotected, False otherwise."""
        if self._procheck(name):
            self._protected_attr = [
                attr for attr in self._protected_attr if attr.lower() != name.lower()
            ]
            return True
        return False

    def grab(self, name: str, full_del: bool = False, default=None):
        """Get `name` then delete or null. `full_del` (bool) if True delete. Returns value or default."""
        if self.hasprop(name, False):
            val = getattr(self, name)
            if full_del:
                delattr(self, name)
            else:
                setattr(self, name, None)
            return val
        return default

    def ograb(self, name: str, full_del: bool = False, default=None):
        """Get any `name` then delete or null. `full_del` (bool) if True delete. Returns value or default."""
        if self.hasprop(name, True):
            val = getattr(self, name)
            if full_del:
                delattr(self, name)
            else:
                setattr(self, name, None)
            return val
        return default

    def _procheck(self, name) -> bool:
        """Return True if `name` is protected or banned."""
        return in_lower_list(name, mergel(self._protected_attr, self._banned_attr))

    def as_dict(self, include_protected: bool = True) -> dict:
        """Return dict of attrs. `include_protected` (bool) to include protected."""
        result = {}
        for k, v in self.__dict__.items():
            if k in self._banned_attr:
                continue
            if not include_protected and in_lower_list(k, self._protected_attr):
                continue
            result[k] = v
        return result

    def __repr__(self) -> str:
        """Return repr string."""
        visible = self.as_dict()
        return f"<Data: {visible}>"

    def __str__(self) -> str:
        """Return str of key: value pairs."""
        items = self.as_dict()
        if not items:
            return "No Properties in Data Class"
        lines = [f"{k}: {v}" for k, v in items.items()]
        return "\n".join(lines) + "\n<----END---->"

    def merge_dict(
        self,
        new_data: dict,
        overwrite_current: bool = False,
        protect_current: bool = False,
        protect_new_added_keys: bool = False
    ) -> bool:
        """Merge `new_data`. `overwrite_current`, `protect_current`, `protect_new_added_keys` (bool). Returns True if changed."""
        changed = False
        for key, val in new_data.items():
            exists = self.hasprop(key, include_protected=False)
            if self._procheck(key):
                continue
            if not overwrite_current and exists:
                continue
            if not self._check_for_type(key,val):
                continue
            setattr(self, key, val)
            changed = True
            if exists and protect_current:
                self._protected_attr.append(key)
            if not exists and protect_new_added_keys:
                self._protected_attr.append(key)
        return changed

    def absorb(
        self,
        other: "Data",
        include_protected: bool = False,
        overwrite: bool = False
    ) -> bool:
        """Absorb from `other`. `include_protected`, `overwrite` (bool). Returns True if changed."""
        if not isinstance(other, Data):
            raise ValueError("Argument must be a Data object.")

        changed = False
        for key, val in other.as_dict(include_protected).items():
            if self._procheck(key):
                continue
            if not self._check_for_type(key,val):
                continue
            exists = self.hasprop(key, include_protected=False)
            if exists and not overwrite:
                continue
            setattr(self, key, val)
            changed = True
        return changed
    
    def get(self,name:str,default=None):
        """Return value of `name` or `default` if not found or protected."""
        if self.hasprop(name,False):
            return getattr(self,name)
        return default
    
    def keys(self,include_protected:bool=True) -> list:
        """Returns a list of property names."""
        return list(self.as_dict(include_protected).keys())
    
    def tags(self, property: str, default) -> list[str]:
        """Returns list of tags (`protected`, `typed`, `kwarg`, `none`) for `property`. If `property` does not exist, returns `default` or `None`."""
        if not hasattr(self, property):
            return default
        tags = []
        if property in self._protected_attr: tags.append("protected")
        if property in self._types: tags.append("typed")
        if property in self._og_protects: tags.append("kwarg")
        if not tags: tags.append("none")
        return tags
    
    def tags_by_key(self) -> dict[str, list]:
        """Return a dict where each property is tagged with `protected`, `typed`, `kwarg`, `none`."""
        return {k:self.tags(k, ["KeyError, Something Went Horribly Wrong."]) for k in self.__dict__.keys() if k not in self._banned_attr}
    
    def keys_by_tag(self) -> dict[str,list[str]]:
        """Return a dict where each tag (`protected`, `typed`, `kwarg`, `none`) maps to a list of properties that have that tag."""
        tags = {
            "protected":set(self.protected_keys(False,False)),
            "typed":set(self.typed_keys(False)),
            "kwarg":set(self.kwarg_keys(False))
        }
        ret:dict[str,list[str]] = {"protected":[],"typed":[],"kwarg":[],"none":[]}

        for k in (k for k in self.__dict__.keys() if k not in self._banned_attr):
            matched = False
            for tag, keys in tags.items():
                if k in keys:
                    ret[tag].append(k)
                    matched = True
            if not matched:
                ret["none"].append(k)
        
        return ret
    
    def bundle_keys(self, protected_tag: bool = True, typed_tag: bool = True, kwarg_tag: bool = True, no_tags: bool = True) -> list[str]:
        """Return a list of property names that match the given tag flags: `protected`, `typed`, `kwarg`, or `untagged`."""
        from .functional_utils.bool import all_bool
        if all_bool(True, protected_tag, typed_tag, kwarg_tag, no_tags):
            return [k for k in self.__dict__.keys() if k not in self._banned_attr]
        ret: list[str] = []
        seen: set[str] = set()
        if protected_tag:
            for k in self.protected_keys(False, False):
                if k not in seen:
                    ret.append(k)
                    seen.add(k)
        if typed_tag:
            for k in self.typed_keys(False):
                if k not in seen:
                    ret.append(k)
                    seen.add(k)
        if kwarg_tag:
            for k in self.kwarg_keys(False):
                if k not in seen:
                    ret.append(k)
                    seen.add(k)
        if no_tags:
            tagged = set(self.protected_keys(False, False)) | set(self.typed_keys(False)) | set(self.kwarg_keys(False))
            for k in (k for k in self.__dict__.keys() if k not in self._banned_attr and k not in tagged):
                ret.append(k)
        return ret
    
    def protected_keys(self, only_typed: bool=False, include_kwargs: bool=False) -> list[str]:
        """Return protected keys. If only_typed, only those also in `_types`. If include_kwargs, include original kwargs."""
        keys = list(self._protected_attr)
        if not include_kwargs:
            keys = [k for k in keys if k not in self._og_protects]
        if only_typed:
            keys = [k for k in keys if k in self._types]
        return keys
    
    def typed_keys(self,only_protected:bool=False) -> list[str]:
        """Return list of type-locked keys. If `only_protected`, only include keys that are also protected."""
        return list(self._types.keys()) if not only_protected else [k for k in self._types.keys() if self._procheck(k)]

    def kwarg_keys(self,only_protected:bool=False) -> list[str]:
        """Return list of original kwargs. If `only_protected`, only include kwargs that are also protected."""
        return list(self._og_protects.keys()) if not only_protected else [k for k in self._og_protects.keys() if self._procheck(k)]
    
    def unprotected_keys(self,include_typed:bool=False,include_kwargs:bool=True) -> list[str]:
        """Return list of unprotected keys. Excludes type-locked or kwarg keys unless included via flags."""
        ret:list = clean_values([k for k in self.__dict__.keys() if not self._procheck(k)],mergel(list(self.typed_keys) if not include_typed else [],
                                                                                                  list(self._og_protects.keys()) if not include_kwargs else []))
        return ret


    def swap(self, property: str, new_val, default=None):
        """Set `property` to `new_val`. Returns old value or `default` if it did not exist."""
        existed = property in self.__dict__
        old = self.__dict__.get(property, None)
        if self._check_for_type(property,new_val):
            setattr(self, property, new_val)
        else:
            self._typederr(property,new_val)
        return old if existed else default
    
    def _check_for_type(self,property:str,new_val) -> bool:
        """Internal method to check if `new_val` is the correct type if `property` is locked. returns bool."""
        proptype = self._types.get(property)
        if proptype:
            return isinstance(new_val,proptype)
        return True

    def _typederr(self,property,new,_raise:bool=False):
        if property not in self._types:
            print(f"{property} has no type lock.")
        if _raise:
            raise ValueError(f"{property} has locked type as: {self._types[property]} but new value has type: {type(new)}.")
        else:
            print(f"{property} has locked type as: {self._types[property]} but new value has type: {type(new)}.")
    
    def __getitem__(self, key):
        """Return value for `key` (same as `get`)."""
        return getattr(self, key)

    def __setitem__(self, key, value):
        """Set `key` to `value` (respects protection & typing)."""
        self.set(key, value)

    def __delitem__(self, key):
        """Delete `key` (respects protection)."""
        self.erase(key)

    def __contains__(self, key) -> bool:
        """Return True if `key` exists (and is not protected when checking)."""
        return self.hasprop(key)

    def __len__(self) -> int:
        """Return count of non‑banned properties."""
        return len(self.as_dict())

    def __iter__(self):
        """Iterate over property names."""
        yield from self.as_dict().keys()

    def __bool__(self) -> bool:
        """True if there’s at least one property."""
        return bool(self.as_dict())

    def __eq__(self, other) -> bool:
        """Compare two Data objects by their visible contents."""
        return isinstance(other, Data) and self.as_dict() == other.as_dict()

    def items(self):
        """Return (key, value) pairs as a view."""
        return self.as_dict().items()

    def keys(self) -> list[str]:
        """Return list of property names."""
        return list(self.as_dict().keys())

    def values(self) -> list:
        """Return list of property values."""
        return list(self.as_dict().values())

    def clear(self):
        """Remove all non‑banned, non‑protected properties."""
        for k in list(self.as_dict().keys()):
            self.erase(k)

    def update(self, other: dict):
        """
        Update from `other` dict (like dict.update),
        respecting protection & typing. Returns None.
        """
        for k, v in other.items():
            self.set(k, v)
    
    def clone(self) -> "Data":
        """Returns an exact copy of this Data object,
        preserving protections, types, kwargs, original kwargs, etc."""
        return Data(data_dictionary=self.export())

    def export(self) -> dict:
        """
        Create a dict snapshot of this Data instance, encoding:
          - plain values for untagged keys
          - {"value": ..., "tags": [...]} for keys that are protected, typed or kwargs
        You can pass the returned dict straight back into Data(...) (with no kwargs)
        and it will rebuild the same protection/typing/kwarg setup.
        """
        out: dict = {}
        # use as_dict(include_protected=True) so we grab everything except internals
        for key, val in self.as_dict(include_protected=True).items():
            tags: list[str] = []
            if key in self._protected_attr:
                tags.append("protected")
            if key in self._types:
                tags.append("typed")
            if key in self._og_protects:
                tags.append("kwarg")
            if tags:
                out[key] = {"value": val, "tags": tags}
            else:
                out[key] = val
        return out
    