#!/usr/bin/env python
"""
logger.py: provides logging methods
"""

# from python lib
import logging
import sys
import os


class Log:
    """
    Singleton class to create log object
    """
    log = None

    def __init__(self):
        if self.__class__.log is None:
            self._initialise()

    def _initialise(self):
        level = 'DEBUG'
        logger = logging.getLogger('qcs')
        logger.setLevel(level)
        
        # create stream handler
        sh = logging.StreamHandler(sys.stdout)
        
        # create formatter
        formatter = logging.Formatter(
                    '%(asctime)s %(levelname)s %(funcName)s %(message)s')
        
        # add formatter to sh
        sh.setFormatter(formatter)
    
        # add sh to logger
        logger.addHandler(sh)
        self.logger = logger

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)
  
    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)
  
    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)
  
    def warn(self, *args, **kwargs):
        self.logger.warn(*args, **kwargs)
  
    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)
  
    def critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs)


if __name__ == '__main__':
    print("Module loaded successfully")
    if os.environ.get('USE_ROBOT_LOGGER', None) == "True":
        from lib.log.logger import Log
        log = Log()
    else:
        log = Log()

    # some sample tests
    print("I'm not using any logger")
    log.info("This is info line")
    log.debug("This is debug line")
    log.error("This is error line")

