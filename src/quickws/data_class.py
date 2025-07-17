from .utils import in_lower_list, in_and_not_in, mergel, clean_value, clean_values

class Data:
    """
    A flexible key-value store with dynamic attribute access, protection, and controlled deletion.

    Attributes:
        _og_list (dict): The original dictionary passed in.
        _og_protects (dict): Named protected attributes set via kwargs.
        _banned_attr (list): Internal names that cannot be modified.
        _protected_attr (list): Keys marked as protected and excluded from some operations.
    """

    def __init__(self, data_dictionary: dict, **kwargs):
        """
        Initialize the Data object with a dictionary and optionally protected named kwargs.
        """
        self._og_list: dict[str] = data_dictionary
        self._og_protects: dict[str] = kwargs
        self._banned_attr: list[str] = [
            "_og_list", "_og_protects", "_banned_attr", "_protected_attr"
        ]
        self._protected_attr: list[str] = list(kwargs.keys())

        for k, v in kwargs.items():
            if k not in self._banned_attr:
                setattr(self, k, v)

        for key, val in data_dictionary.items():
            if key not in mergel(self._banned_attr, self._protected_attr):
                setattr(self, key, val)

    def hasprop(self, name: str, include_protected: bool = True) -> bool:
        """
        Check if a property exists, optionally excluding protected attributes.
        """
        allowed = clean_values(
            self.__dict__.keys(),
            mergel(self._banned_attr, [] if include_protected else self._protected_attr)
        )
        return name in allowed

    def oset(self, attr: str, newval) -> bool:
        """
        Same as `.set()` method, but allows you to overwrite protected properties as well.

        Returns:
            True if attr existed and was overwritten, False otherwise.
        """
        if hasattr(self, attr):
            setattr(self, attr, newval)
            return True
        return False

    def odel(self, attr: str) -> bool:
        """
        Delete an attribute if it exists.

        Returns:
            True if attr existed and was deleted, False otherwise.
        """
        if hasattr(self, attr):
            delattr(self, attr)
            return True
        return False

    def set(self, name: str, val) -> bool:
        """
        Set an attribute unless it is protected or banned.

        Returns:
            True if attribute was set, False if blocked by protection.
        """
        if not self._procheck(name):
            setattr(self, name, val)
            return True
        return False
    
    def sets(self,**kwargs):
        """Sets multiple attributes passed in as kwargs unless they are protected or banned.
        
        Returns:
            `int` of how many successfully set.
        """
        count = 0
        for k, v in kwargs.items():
            if self.set(k,v):
                count += 1
        return count
    
    def osets(self,**kwargs):
        """
        Same as `.sets()` but allows you to overwrite protected properties as well.

        Returns:
            `int` of how many successfully set.
        
        """
        count = 0
        for k,v in kwargs.items():
            if self.oset(k,v):
                count += 1
        return count

    def protect(self, name: str) -> bool:
        """
        Add an attribute to the protected list.

        Returns:
            True if attribute was newly protected, False if already protected/banned.
        """
        if not self._procheck(name):
            self._protected_attr.append(name)
            return True
        return False

    def unprotect(self, name: str) -> bool:
        """
        Remove a protected attribute, unless it was originally defined via kwargs.

        Returns:
            True if attribute was unprotected, False otherwise.
        """
        if self._procheck(name) and not in_lower_list(name, self._og_protects.keys()):
            self._protected_attr = [
                attr for attr in self._protected_attr if attr.lower() != name.lower()
            ]
            return True
        return False

    def ounprotect(self, name: str) -> bool:
        """
        Force remove protection regardless of original protection status.

        Returns:
            True if attribute was unprotected, False otherwise.
        """
        if self._procheck(name):
            self._protected_attr = [
                attr for attr in self._protected_attr if attr.lower() != name.lower()
            ]
            return True
        return False

    def grab(self, name: str, full_del: bool = False,default=None):
        """
        Retrieve and optionally delete a non-protected attribute.

        Returns:
            The value if it existed (and then removed or nulled), else returns default if provided or None.
        """
        if self.hasprop(name, False):
            val = getattr(self, name)
            if full_del:
                delattr(self, name)
            else:
                setattr(self, name, None)
            return val
        return default

    def ograb(self, name: str, full_del: bool = False, default=None):
        """
        Retrieve and optionally delete any attribute, including protected ones.

        Returns:
            The value if it existed (and then removed or nulled), else returns default if provided or None.
        """
        if self.hasprop(name, True):
            val = getattr(self, name)
            if full_del:
                delattr(self, name)
            else:
                setattr(self, name, None)
            return val
        return default

    def _procheck(self, name) -> bool:
        """
        Internal check for whether a name is protected or banned.
        """
        return in_lower_list(name, mergel(self._protected_attr, self._banned_attr))

    def as_dict(self, include_protected: bool = True) -> dict:
        """
        Return a dictionary of all non-internal attributes.

        Args:
            include_protected: If False, protected attributes are excluded.

        Returns:
            A dict of key-value pairs.
        """
        result = {}
        for k, v in self.__dict__.items():
            if k in self._banned_attr:
                continue
            if not include_protected and in_lower_list(k, self._protected_attr):
                continue
            result[k] = v
        return result

    def __repr__(self) -> str:
        """
        Return a readable string of the Data object's contents.
        """
        visible = self.as_dict()
        return f"<Data: {visible}>"

    def __str__(self) -> str:
        """
        Return a multi-line string of key: value pairs, or a message if empty.
        """
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
        """
        Merge key-value pairs from another dictionary into this one.

        Args:
            new_data: Dictionary to merge in.
            overwrite_current: If False, existing keys are not overwritten.
            protect_current: If True, re-setting an existing key also protects it.
            protect_new_added_keys: If True, all newly added keys are protected.

        Returns:
            True if any keys were added or updated, False otherwise.
        """
        changed = False
        for key, val in new_data.items():
            exists = self.hasprop(key, include_protected=False)
            if self._procheck(key):
                continue
            if not overwrite_current and exists:
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
        """
        Absorb key-value pairs from another Data object.

        Args:
            other: The other Data object to absorb from.
            include_protected: Whether to include protected keys from `other`.
            overwrite: Whether to overwrite existing (non-protected) keys in `self`.

        Returns:
            True if any keys were added or overwritten, False otherwise.
        """
        if not isinstance(other, Data):
            raise ValueError("Argument must be a Data object.")

        changed = False
        for key, val in other.as_dict(include_protected).items():
            if self._procheck(key):
                continue
            exists = self.hasprop(key, include_protected=False)
            if exists and not overwrite:
                continue
            setattr(self, key, val)
            changed = True
        return changed
