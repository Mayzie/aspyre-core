import string
from collections import MutableMapping, OrderedDict, Mapping


class AspyreDictImmutable(MutableMapping):
    def __init__(self, old_dict=None):
        if isinstance(old_dict, AspyreDictImmutable):
            self.__dict__.update(old_dict.__dict__)

            if '__history' in self.__dict__:
                del self.__dict__['__history']
        elif isinstance(old_dict, Mapping) or isinstance(old_dict, dict):
            self.__dict__.update(old_dict)
        elif old_dict is not None:
            raise TypeError(f"'{self.__class__.__name__}' does not support a 'old_dict' that isn't a dict, Mapping, or None. You gave it a type of '{type(old_dict)}'")
        else:
            self.__dict__['__history'] = []

    def __find_key__(self, key):
        key_f = ''.join(char for char in str(key).lower() if char in string.ascii_lowercase)

        for cls_key in self.__dict__.keys():
            if key_f == ''.join(char for char in cls_key.lower() if char in string.ascii_lowercase):
                return True, cls_key

        return False, key

    def __getitem__(self, key):
        found, key = self.__class__.__find_key__(self, key)
        if found:
            return self.__dict__[key]
        else:
            return None

    def __delitem__(self, key):
        raise TypeError(f"'{self.__class__.__name__}' object does not support item deletion.")

    def __setitem__(self, key, value):
        raise TypeError(f"'{self.__class__.__name__}' object does not support item assignment.")

    def __contains__(self, key):
        found, _ = self.__class__.__find_key__(self, key)
        return found

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __getattr__(self, key):
        return self.__class__.__getitem__(self, key)

    def __delattr__(self, key):
        return self.__class__.__delitem__(self, key)

    def __setattr__(self, key, value):
        return self.__class__.__setitem__(self, key, value)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self, indent=4, level=1):
        if level == 0:
            level = 1

        ind = "\n" + ' ' * (indent * level)
        s = self.__class__.__name__ + '({'
        for key, value in self.__dict__.items():
            if key == '__history':
                continue
            if isinstance(value, AspyreDictImmutable):
                s += ind + f"'{key}': " + value.__repr__(indent=indent, level=(level + 1)) + ","
            else:
                s += ind + f"'{key}': " + value.__repr__() + ","

        s += ("\n" + " " * (indent * (level - 1))) + "})"

        return s

    def __str__(self):
        return self.__repr__()

    def __add__(self, other):
        if isinstance(other, Mapping) or isinstance(other, dict):
            result = self.__class__(self)
            result.update(other)

            return result
        elif isinstance(other, list):
            result = self.__class__(self)
            for item in other:
                if isinstance(other, Mapping) or isinstance(other, dict):
                    result.update(item)
                else:
                    raise TypeError(f"Unsupported type addition {type(other)} to AspyreDict. Must be a map or dict-like object, or a list of those.")

            return result
        else:
            raise TypeError(f"Unsupported type addition {type(other)} to AspyreDict. Must be a map or dict-like object, or a list of those.")

    def __sub__(self, other):
        if isinstance(other, str):
            result = self.__class__(self)
            if other in result:
                del result.__dict__[other]

            return result
        elif isinstance(other, list):
            result = self.__class__(self)
            for item in other:
                if isinstance(item, str):
                    del result[item]
                else:
                    raise TypeError(f"Unsupported type substraction {type(other)} to AspyreDict. Must be a string, or a list of strings.")

            return result
        else:
            raise TypeError(f"Unsupported type substraction {type(other)} to AspyreDict. Must be a string, or a list of strings.")

    def __eq__(self, other):
        for key, value in self.__dict__.items():
            if key not in other:
                return False

            if value != other[key]:
                return False

        for key, value in other.items():
            if key not in self:
                return False

        return True


class AspyreDict(AspyreDictImmutable):
    def __delitem__(self, key):
        found, key = super().__find_key__(key)

        if found:
            del self.__dict__[key]

    def __setitem__(self, key, value):
        _, key = super().__find_key__(key)
        if isinstance(value, AspyreDictImmutable):
            self.__dict__[key] = value
        elif isinstance(value, dict) or isinstance(value, Mapping):
            self.__dict__[key] = self.__class__(value)
        else:
            self.__dict__[key] = value

    
class AspyreDictHistory(AspyreDict):
    def __init__(self, old_dict=None):
        super().__init__(old_dict)

        if isinstance(old_dict, AspyreDictHistory):
            self.__dict__['__history'] = list(old_dict.__dict__['__history'])
        else:
            self.__dict__['__history'] = [self]

    def __find_key__(self, key):
        key_f = ''.join(char for char in str(key).lower() if char in string.ascii_lowercase)

        for cls_key in self.__dict__.keys():
            if cls_key == '__history':
                continue

            if key_f == cls_key:
                return True, cls_key

        return False, key

    def __getitem__(self, key):
        key_l = key.lower()
        if key_l == '__history':
            return

        return super().__getitem__(key)

    def __setitem__(self, key, value):
        key_l = key.lower()
        if key_l == '__history':
            raise AttributeError(f"Cannot modify private property '{self.__class__.__name__}.__history'.")

        super().__setitem__(key, value)

    def __delitem__(self, key):
        key_l = key.lower()
        if key_l == '__history':
            raise AttributeError(f"Cannot delete private property '{self.__class__.__name__}.__history'.")

        super().__delitem__(key)

    def __getattribute__(self, key):
        key_l = key.lower()
        if key_l == '__history':
            return

        return super().__getattribute__(key)

    def get_current_version(self):
        return len(self.__dict__['__history'])

    def rollback(self, version=-1):
        state = self.__dict__['__history'][version]
        history = state.__dict__['__history']
        del state.__dict__['__history']

        self.__dict__.clear()
        self.__dict__.update(state.__dict__)
        self.__dict__['__history'] = list(history)

    def save(self):
        self.__dict__['__history'].append(self.__class__(self))
        return self.get_current_version()
