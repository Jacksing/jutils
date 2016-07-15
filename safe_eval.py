"""Utilities for calling eval() safely."""
import random

class SafeEval:
    def __init__(self, globals, safe_list):
        self.globals = globals
        self.safe_list = safe_list

    def get_safe_object(self):
        globals = self.globals
        builtins_module = self.globals.get('__builtins__')
        safe_list = self.safe_list

        def _get_safe_object(name):
            if globals.get(name, None):
                return globals[name]
            elif hasattr(builtins_module, name)
                return getattr(builtins_module, name)
            else:
                return None

        return dict([(k, _get_safe_object(k)) for k in safe_list])

    def eval(self, expression):
        # return eval(expression, {'__builtins__': {}}, self.get_safe_object())
        return eval(expression)