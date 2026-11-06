"""Minimal pytest compatibility shim for offline environment."""
import sys, os, inspect, re, tempfile, shutil
from pathlib import Path

class raises:
    def __init__(self, expected_exc, match=None):
        self.expected_exc = expected_exc
        self.match = match
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(f'Expected exception {self.expected_exc} but none was raised')
        if not issubclass(exc_type, self.expected_exc):
            return False
        if self.match:
            if not re.search(self.match, str(exc_val)):
                raise AssertionError(f'Pattern {self.match!r} does not match {str(exc_val)!r}')
        return True

def fixture(func=None, scope='function', params=None, autouse=False, ids=None, name=None):
    if func is None:
        def dec(f):
            f.__is_fixture__ = True
            return f
        return dec
    func.__is_fixture__ = True
    return func

def skip(msg=''):
    raise SkipTest(msg)

class SkipTest(Exception):
    pass

def fail(msg=''):
    raise AssertionError(msg)

class mark:
    @staticmethod
    def mysql(func):
        func.__mysql__ = True
        return func
    @staticmethod
    def parametrize(argnames, argvalues):
        def dec(func):
            func.__parametrize__ = (argnames, argvalues)
            return func
        return dec

def main():
    pass
