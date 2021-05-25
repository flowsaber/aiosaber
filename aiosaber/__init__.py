__version__ = '0.0.1.1'

import warnings

import uvloop

# noinspection PyUnresolvedReferences
from .channel import *
# noinspection PyUnresolvedReferences
from .flow import *
# noinspection PyUnresolvedReferences
from .middleware import BaseHandler, BaseExecutor, BaseBuilder
# noinspection PyUnresolvedReferences
from .operators import *
# noinspection PyUnresolvedReferences
from .task import *

uvloop.install()
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=UserWarning)
