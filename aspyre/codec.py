from abc import ABCMeta, abstractmethod

import dictionary
import error
import json

class Codec(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self):
        """
        Metaclass for Aspyre codecs.

        All codecs must inherit from this class and implement its methods.
        """
        pass

    @abstractmethod
    def encode(self, output):
        """
        Converts the result data to a bytes-like representation to be returned.

        Args:
            output: The culminated data returned from each of the Aspyre handlers, or an (Aspyre) exception.

        Returns:
            A bytes-like object of the encoded data to be returned, or a tuple where the first element
            is a bytes-like object and the second element being a dictionary of any HTTP headers to be
            appended to the result.
        """
        pass

    @abstractmethod
    def decode(self, input, headers):
        """
        Converts incoming data to an object that is expected to be readable by each of the Aspyre handlers.

        Args:
            input (`str`): A string of the input data.
            headers (`dict`): Incoming HTTP headers (case-insensitive).
        """
        pass

    @abstractmethod
    def get_class(self):
        """
        Returns an instantiated class that the Aspyre handlers are expected to operate on.

        Returns an instantiated class that the Aspyre handlers are expected to operate on.
        
        For example, if we're receiving and processing JSON data, we might want to return an instantiated
        (but empty) dictionary here.
        """
        pass


class AspyreJSONCodec(Codec):
    def __init__(self, strict=False):
        self.strict = strict

    def encode(self, output):
        headers = {
            'Content-Type': 'application/json'
        }

        return bytes()

    def decode(self, input, headers):
        if not (self.strict and getattr(headers, 'content-type', None) == 'application/json'):
            raise error.BadRequest(message='Missing or invalid Content-Type provided.')

        return dictionary.AspyreDictImmutable()

    def get_class(self):
        return dictionary.AspyreDictHistory()
