import asyncio

### Depreciated - Old Data Class

class userData:
    """
    A flexible container class for storing user-defined attributes.

    Parameters:
        data (dict): A dictionary containing key-value pairs to set as attributes.
                     Only string keys are accepted. Protected attributes such as 
                     'uid' and 'ws' will not be overwritten.

    Notes:
        - Auto generated with passed in user_data dictionary when user connects.
        - All keys in the input dictionary will be set as attributes unless protected.
        - Protected keys are case-insensitive and will be skipped.
    """
    def __init__(self, data: dict = {}):
        self._protected_attr: list[str] = ["uid", "ws"]
        for key, val in data.items():
            if not isinstance(key, str):
                continue
            if key.lower() in self._protected_attr:
                print("Cannot override protected attribute:", key.lower())
                continue
            setattr(self, key, val)

    def get(self, key: str, default=None):
        """
        Retrieves the value of the specified attribute.

        Parameters:
            key (str): The attribute name to retrieve.
            default (any, optional): A default value to return if the attribute is not found.

        Returns:
            The value of the attribute if found; otherwise, the provided default (or None).
        """
        val = self.__dict__.get(key)
        return val if val else default

    def set(self, key: str, new_val: any, create_if_not_present: bool = True):
        """
        Sets an existing attribute's value to the given value.

        Parameters:
            key (str): The attribute name to set.
            new_val (any): The new value for the attribute.
            create_if_not_present (bool, optional): Whether to allow creation of a new
                                                    attribute if it does not exist. 
                                                    Defaults to True.

        Notes:
            - Will not set values for protected keys.
        """
        if self._keycheck(key):
            if not create_if_not_present and not self.__dict__.get(key):
                return
            self.__dict__[key] = new_val
        print("Cannot override attribute:", key)

    def gets(self, keys: list[str], default=None):
        """
        Retrieves multiple attributes at once.

        Parameters:
            keys (list[str]): A list of attribute names to retrieve.
            default (any, optional): A default value to use for missing attributes.
                                     If a dictionary is passed and contains the key,
                                     its value is used instead of None.

        Returns:
            dict: A dictionary of { key: value } pairs.
        """
        data: dict = {}
        if isinstance(keys, list):
            for key in keys:
                if isinstance(key, str):
                    data[key] = self.get(key)
        return data

    def sets(self,data:dict):
        for key, val in data.items():
            if isinstance(key,str):
                self.set(key,val,True)
            continue

    def getall(self):
        """
        Retrieves all stored attributes and their values.

        Returns:
            dict: A dictionary containing all attribute names and values.
        """
        data: dict = {}
        for key, value in self.__dict__.items():
            data[key] = value
        return data

    def _keycheck(self, key, admin_check: bool = True) -> bool:
        """
        Internal method to validate a key before modification.

        Parameters:
            key (any): The attribute key to check.
            admin_check (bool): Whether to enforce protected attribute restriction.

        Returns:
            bool: True if the key is valid and allowed; False otherwise.
        """
        if not isinstance(key, str):
            return False
        if not admin_check:
            k = key.lower()
            if k in self._protected_attr:
                return False
        return True

    def __str__(self):
        """
        Returns a human-readable string of all stored attributes.

        Returns:
            str: A formatted string listing all attribute keys and their values.
        """
        msg: str = ""
        for key, value in self.__dict__.items():
            msg += f"{key}: {value}\n"
        return msg
