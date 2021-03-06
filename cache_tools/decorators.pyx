# coding: utf-8

from __future__ import unicode_literals
import cython
from django.core.cache import cache
from .utils cimport get_cache_key, get_object_cache_key


__all__ = ('model_method_cached',)


cdef cache_get = cache.get
cdef cache_set = cache.set


def model_method_cached(bytes id_attr=b'pk'):
    def decorator(method):
        @cython.locals(args=tuple, kwargs=dict)
        def wrapper(self, *args, **kwargs):
            cdef bytes object_cache_key
            cdef list object_keys
            cdef cache_key = get_cache_key(method, self, args, kwargs, id_attr)
            out = cache_get(cache_key)
            if out is None:
                object_cache_key = get_object_cache_key(self, id_attr)
                object_keys = cache_get(object_cache_key, [])
                object_keys.append(cache_key)
                cache_set(object_cache_key, object_keys, 0)
                out = method(self, *args, **kwargs)
                cache_set(cache_key, out, 0)
            return out
        return wrapper
    return decorator
