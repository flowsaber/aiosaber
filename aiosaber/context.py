import contextvars
from collections import UserDict

context_var = contextvars.ContextVar("aiosaber_context")


class ContextNotExistError(LookupError):
    pass


class Context(UserDict):
    PASS_ARGS = ['data', 'store']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = {}

    @property
    def data(self):
        try:
            return context_var.get()
        except LookupError:
            raise ContextNotExistError("Context does not exist, this often happens in cross process situations.")

    @data.setter
    def data(self, dic):
        context_var.set(dic)

    @property
    def coms(self):
        return self.setdefault('_coms', [])

    def __getattr__(self, item):
        return self[item]

    def __delattr__(self, item):
        del self[item]

    def __setattr__(self, key, value):
        if key.startswith('_') or key in self.__class__.PASS_ARGS:
            # __setattr__ prevail property.__set__
            if hasattr(type(self), key):
                object.__setattr__(self, key, value)
            else:
                self.__dict__[key] = value
        else:
            self[key] = value


context = Context()
