import abc
import re
from collections import Mapping

import datetime
import uuid
import base64


__re_type = type(re.compile(''))
__default_types__ = {
    'str': str,
    'strl': str.lower,
    'stru': str.upper,
    'int': int,
    'float': float,
    'date': lambda s: datetime.date(*map(int, s.split('-'))),
    'timestamp': lambda s: datetime.datetime.fromtimestamp(int(s)),
    'uuid': uuid.UUID,
    'base64': lambda s: str(base64.urlsafe_b64decode(s), 'ascii'),
}


class URLClass(metaclass=abc.ABCMeta):
    """Metaclass that must be inherited from when creating a custom URL class.
    
    A metaclass that defines methods that must be implemented by classes which inherit from it.

    """

    @abc.abstractmethod
    def __init__(self, types=None):
        pass

    @abc.abstractmethod
    def add_route(self, cls, *args):
        pass

    @abc.abstractmethod
    def find(self, host, path):
        pass


class Regex(URLClass):
    """A regular expression powered URL class.

    Allows the developer to match either the host or path (or both!) portions of an incoming URL request
    utilsing Python's powerful regular expression library.

    Matches are defined as a tuple of two strings `(host, path)`, or one `path` string. Paths must begin
    with a forward slash. (Both) Strings have to be a valid Python regular expression. If a URL contains
    arguments which must be passed into its respective function(s), use the ``group`` method below.

    Args:
        types (`dict`): A key-value data structure where the keys are the data types to be supported in the
            URL, and the values are callables which is the method used to convert the string to the necessary
            data type.

            If no `types` value is supplied, then the default is to use the `builtins` dictionary, which
            contains basic data types like `str`, and `int`.

    """

    __separator__ = '0_d_collis_1'  # Mangling workaround for Python regex named groups not allowing a ':' character.
    __re_group_match = re.compile("\(\?P\<([^\>\:]+)\:?([^\>]*)\>([^\)]+)\)")

    def __init__(self, types=None):
        self.__url_list = []
        if types and not (isinstance(types, dict) or isinstance(types, Mapping)):
            raise TypeError("'types' in URLClass init does not have a dict-like type. It is of type '{}'.".format(type(types)))

        self.__types = types if types else {}

    def __replacement_strategy__(match):
        # (?P<type:name>regex)
        type = match.group(1)
        name = match.group(2)
        regex = match.group(3)

        if not name:
            return "(?P<{}>{})".format(type, regex)
        else:
            return "(?<{}{}{}>{})".format(type, Regex.__seperator__, name, regex)

    def add_route(self, cls, *urls):
        """Adds a handler class for a variety of regular expression-based URLs.

        Adds a handler that will run when an incoming request has matched any of those listed in the ``*urls``
        variable argument list.

        To parse URL arguments and pass them into the methods of the class, ``cls``, you must use the ``group``
        function below within your regular expression string, or alternatively manually implement this
        functionality using regular expression named groups only (see the Python documentation for the
        `re` module for more information). If you want to extract an argument from the host portion of a URL,
        you **must** manually implement a named group (i.e. not using the ``group()`` method).

        Args:
            cls (`Aspyre.Resource`): A class inheriting from `aspyre.Resource` that will handle requests which match
                the regular expressions in the ``*urls`` variable argument list.
            *urls: Strings (paths), or a tuple of two strings `(host, path)`, that represent a regular 
                expression to be matched against. If supplying a path string only, then it *must* begin with
                a forward slash. If supplying a host-path tuple pair, then the first string will match the
                host portion of a URL (e.g. `sub.example.com`), and the second string will match the path
                portion of a URL (which like a single path string, must also begin with a forward slash).

        Returns:
            Nothing.

        Raises:
            ValueError: Raised when the input arguments for the variable argument list ``*urls`` are
                malformed.

                For example:
                    - when supplying a tuple, if the first or second element of the tuple,
                    - when supplying an element that is not a tuple and not a string,
                    - when supplying a string (by itself, or within a tuple) that is supposed to match a path
                    that does not begin with a forward slash.

        """

        for url in urls:
            host = None
            path = None
            if isinstance(url, tuple) and len(url) == 2:
                if url[0] is not None and not isinstance(url[0], str):
                    raise ValueError("URL specified in a tuple (host, path) must be a string. You gave '{}' of type '{}' as a first argument.".format(url[0], type(url[0]).__name__))
                if url[1] is not None and not isinstance(url[1], str):
                    raise ValueError("URL specified in a tuple (host, path) must be a string. You gave '{}' of type '{}' as a second argument.".format(url[1], type(url[1]).__name__))

                if url[0]:
                    url[0] = Regex.__re_group_match.sub(Regex.__replacement_strategy__, url[0])
                    host = re.compile(url[0])
                if url[1]:
                    if url[1][0] == '/':  # Check that the path string begins with a '/'
                        url[1] = Regex.__re_group_match.sub(Regex.__replacement_strategy__, url[1][1:])

                        path = re.compile(url[1])
                    else:
                        raise ValueError("URL path string's  must begin with a '/'. You gave '{}'.".format(url[1]))
            elif isinstance(url, str):
                if url[0] == '/':  # Check that the path string begins with a '/'
                    url = Regex.__re_group_match.sub(Regex.__replacement_strategy__, url[1:])
                    path = re.compile(url)
                else:
                    raise ValueError("URL string's can only match paths and must begin with a '/'. You gave '{}'.".format(url))
            else:
                raise ValueError("URL must either be a string representing a path or a tuple representing (host, tuple). You gave '{}' of type '{}'.".format(url, type(url).__name__))
                
            self.__url_list.append(((host, path), cls))

    def find(self, host, path):
        """Matches an incoming URL, and if found, will return all classes in the order declared that matches
        the expression.

        Will return all classes in a list that will handle the request if it matches the given expression(s).
        Note that this method is rather dumb, in the fact that it will return *all* classes, even when they
        may not be able to handle the request (i.e. no GET method handler, etc), as that information is
        unavailable to this method and should be handled elsewhere.

        Note that you must supply a host, path, or both. At least one must be not empty or None.

        Args:
            host (`str`): The host portion of a URL to match (optional).
            path (`str`): The path portion of a URL to match (optional).

        Returns:
            list (`aspyre.Resource`): A list structure that contains all the classes that can handle the
            the request in the order declared.

        Raises:
            AttributeError: Raised when a named group does not have a key that can be found in the ``types``
                dictionary, and therefore a conversion to the desired type cannot be performed.

        """

        handlers = []

        for u in self.__url_list:
            cls = u[1]  # Extract the handling class.
            u = u[0]  # Extract the URL.

            m1, m2 = None, None  # Match 1, Match 2
            args = {}
            if u[0]:  # Match 1 (match host)
                m1 = re.fullmatch(u[0], host)
                if m1:
                    args.update(m1.groupdict())

            if u[1]:  # Match 2 (match path)
                m2 = re.fullmatch(u[1], path)
                if m2:
                    args.update(m2.groupdict())

            if m1 or m2:
                ret_args = {}  # Return arguments
                for key, value in args.items():
                    # key = key[1:][:-1]  # Remove angle brackets from string.
                    t, name = key.split(Regex.__separator__)  # Type, name
                    if t in self.__types:
                        value = self.__types[t](value)
                    else:
                        func = globals()['__builtins__'][t]
                        if func:
                            value = func(value)
                        else:
                            raise AttributeError("Can't find a callable / type cast function with the name '{}' referenced in URL tuple '{}'.".format(t, u))

                    ret_args[name] = value

                # Make sure that the handler has not already been returned (we don't execute it more than once)
                if cls not in handlers:
                    handlers.append((cls, ret_args))

        return handlers

    @staticmethod
    def group(type, name):
        """Creates a regular expression named group that can be used for URL arguments inside a URL path.

        A simple method that is used to specify URL path arguments within a regular expression that can be
        parsed by the ``find`` method. The first argument must be a string, and refer to a key-value pair
        within the ``types`` class attribute (defined on class creation). The second argument must be the name
        for the given URL argument.

        This method is utilised within the ``Simple`` URL class to convert <str:username> to a valid
        regular expression named group.

        Args:
            type (`str`): A string referencing a key within the ``types`` dictionary.
            name (`str`): What name to give to this argument for future reference.

        Returns:
            str: A string that can be added to a regular expression.
            
                For example, for arguments `type='str'` and `name='username'`, the result would be something
                like: '(?P<str0_d_collis_1username>[^\/]+)' (which will match all characters until the next
                forward slash in the URL).
        """

        return '(?P<' + type + Regex.__separator__ + name + '>[^\/]+)'


class Simple(Regex):
    """A URL class that is designed to handle most use cases with programming ease.

    This URL class should satisfy the needs for most developers. It allows to define routes using Flask-like
    syntax.

    An example of such syntax is: `Simple.add_route(ProductResource, '/products/<int:product_id>')`. If a GET
    request is perfomed on the URL `'/products/1234'`, the `get` method for the `ProductResource` will be
    invoked like `ProductResource.get(context, headers, data, response, product_id=1234)`.

    Args:
        types (`dict`): A key-value data structure where the keys are the data types to be supported in the
            URL, and the values are callables which is the method used to convert the string to the necessary
            data type.

            If no `types` value is supplied, then the default is to use the `builtins` dictionary, which
            contains basic data types like `str`, and `int`.

    """
    __re_args = re.compile('\<[^\>]*\>')

    def __init__(self, types=None):
        super().__init__(types)

    def add_route_advanced(self, cls, *urls):
        """Exposes the ``Regex.add_route`` method for convenience / more advanced usage.
        """

        return super().add_route(cls, *urls)

    def add_route(self, cls, *urls):
        """Appends a new route handler for the url list `*urls`.

        Very similar to ``Regex.add_route``, with the exceptions of it not accepting host, path tuple pairs,
        (only path strings), and specifying URL arguments using Flask-like syntax, using a `<type:name>` syntax.

        Args:
            cls (`Aspyre.Resource`): The class that will handle these routes.
            *urls (`str`): A list of path strings that will be matched against.

        Raises:
            TypeError: Raised when a URL supplied is not of type `str`.
        """
        for url in urls:
            if not isinstance(url, str):
                raise TypeError("URL must be a string type for Simple routing. You gave a type of '{}' for url '{}'.".format(type(url).__name__, url))

            if len(url) > 0 and url[0] == '/':
                url = url[1:]
            if len(url) > 0 and url[-1] == '/':
                url = url[:-1]

            last_index = 0
            parsed_url = '/'
            for m in Simple.__re_args.finditer(url):
                # Copy the existing URL up until the match point.
                parsed_url = parsed_url + re.escape(url[last_index:m.start()])
                # Strip the angle brackets and group key and name.
                key = Simple.group(*(m.group()[1:][:-1].split(':')))  
                # Replace the match with its regex equivalent named group.
                parsed_url = parsed_url + key
                # Recalculate the last_index
                last_index = m.start() + len(m.group())

            if last_index != len(url):
                parsed_url = parsed_url + re.escape(url[last_index:])

            super().add_route(cls, parsed_url)
