#!/usr/bin/env python3.11
import logging
from IPython import start_ipython
from traitlets.config import Config as IPythonConfig

from app.services.analysis import *
from app.db import get_async_session_factory  # noqa

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


session_factory = get_async_session_factory()

# Create a new IPython config object
ipython_config = IPythonConfig()
ipython_config.InteractiveShellApp.extensions = ['autoreload']
ipython_config.InteractiveShellApp.exec_lines = [
    '%autoreload 2',
    'print("Autoreload enabled: modules will be reloaded automatically when changed.")',
    'print("Database session factory available as `session_factory`")'
]

# Starts an ipython shell with access to the variables in this local scope
start_ipython(user_ns=locals(), config=ipython_config)
