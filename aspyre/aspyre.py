import sys
from itertools import product
from collections import OrderedDict
from urllib.parse import parse_qs
from asyncio import coroutine

import error

Methods = {
    'http_methods': ['get', 'post', 'put', 'patch', 'delete'],
    'before_after': ['before', 'after'],
}

Methods['callable'] = Methods['http_methods'] \
                      + Methods['before_after'] \
                      + list(map(lambda x: x[0] + '_' + x[1],
                          product(Methods['before_after'], Methods['http_methods'])
                      ))


class Find:
    @staticmethod
    async def first(host, path, method, instances):
        for instance in instances:
            handlers = instance.find(host, path, method)
            if handlers:
                return handlers, instance

        return None

    @staticmethod
    async def best(host, path, method, instances):
        maximum = -1
        max_handlers = []
        found_instance = None
        for instance in instances:
            handlers = instance.find(host, path, method)
            if len(handlers) > maximum:
                maximum = len(handlers)
                max_handlers = handlers
                found_instance = instance

        return max_handlers


class Aspyre:
    def __init__(self, url_class=None, codec=None, dict_class=None, **instances):
        if not url_class:
            raise ValueError('No URL class has been supplied to this Aspyre object.')

        if not codec:
            raise ValueError('No codec has been supplied to this Aspyre object.')

        self.url_class = url_class
        self.codec = codec
        self.instances = instances

    async def __call__(self, host, path, method, input, headers=None, query_string=None):
        if method not in Methods['http_methods']:
            raise error.NotImplemented(message="The server does not support this HTTP method.")

        handlers = self.find(host, path, method)
        if handlers:
            return self.handle(handlers, input, query_string)
        else:
            raise error.NotFound(message='No matching handler for URL found.')

    async def find(self, host, path, method):
        found_handlers = self.url_class.find(host, path)

        if found_handlers:
            before = 'before_' + method
            after = 'after_' + method

            handlers = OrderedDict()
            handlers['before'] = []
            handlers[before] = []
            handlers[method] = []
            handlers[after] = []
            handlers['after'] = []

            for handler in found_handlers:
                arguments = handler[1]
                handler = handler[0]

                if callable(getattr(handler, 'before', None)):
                    handlers['before'].append((handler.before, arguments))
                if callable(getattr(handler, before, None)):
                    handlers[before].append((getattr(handler, before), arguments))
                if callable(getattr(handler, method, None)):
                    handlers[method].append((getattr(handler, method), arguments))
                if callable(getattr(handler, after, None)):
                    handlers[after].insert(0, (getattr(handler, method), arguments))
                if callable(getattr(handler, 'after', None)):
                    handlers['after'].insert(0, (handler.after, arguments))

            return handlers

        return None

    async def handle(self, handlers, input, headers, query_string):
        if not handlers:
            raise error.NotFound(message="No matching handler for URL found.")

        context = self.dict_class()
        context['arguments'] = parse_qs(query_string) if query_string else None
        context['headers'] = headers

        response = self.codec.get_class()
        in_headers = self.dict_class()

        for key, value in handlers.items():
            for handler in value:
                arguments = handler[1]
                handler = handler[0]
                result = None

                try:
                    result = await handler(context, in_headers, input, response, *arguments)

                    if result is not None and isinstance(result, int):
                        context['http_code'] = result
                except error.Error as e:
                    if e.reraise:
                        return self.codec.encode(e)

                    error = self.dict_class()
                    if e.error_code is not None:
                        error['code'] = e.error_code
                    else:
                        error['code'] = e.http_code

                    if e.message is not None:
                        error['message'] = e.message
                    else:
                        error['message'] = 'An error has occured.'

                    if e.short_name is not None:
                        error['name'] = e.short_name

                    context['error'] = error
                    context['http_code'] = e.http_code
                except Exception as e:
                    return self.codec.encode(e)

        return self.codec.encode(response), context

    @staticmethod
    def __fix_params__(**kwargs):
        result = dict()

        if 'method' in kwargs:
            if kwargs['method'] == 'head':
                result['ignore_response'] = True
                result['method'] = 'get'
            else:
                result['ignore_response'] = False

        if 'path' in kwargs:
            result['path'] = kwargs['path']

            # Remove forward and trailing slash from path (if it is there).
            path = kwargs['path']
            if path:
                if path[0] == '/':
                    result['path'] = result['path'][1:]
                if path[1] == '/':
                    result['path'] = result['path'][:-1]

        return result


class AspyreGroup:
    def __init__(self, codec, find=Find.first):
        if not codec:
            raise ValueError('No codec has been supplied to this AspyreGroup object.')

        self.__instances__ = []

        self.find = find
        self.codec = codec

    def add_instances(self, *args):
        for instance in args:
            if isinstance(instance, Aspyre):
                self.__instances__.append(instance)
            else:
                raise ValueError('AspyreGroup.add_instances requires each argument to be an instantiated class of Aspyre.')

    def add_instance(self, instance):
        if isinstance(instance, Aspyre):
            self.__instances__.append(instance)
        else:
            raise ValueError('AspyreGroup.add_instance requires its argument to be an instantiated class of Aspyre.')

    async def __call__(self, host, path, method, input, headers=None, query_string=None):
        handlers, instance = self.find(host, path, method, self.__instances__)

        if handlers:
            return instance.handle(handlers, input, headers, query_string)
        else:
            return self.codec.encode(error.NotFound(message='No matching handler for URL found.'))
