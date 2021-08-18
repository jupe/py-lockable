"""
Lockable logger module
"""
import logging


def get_logger(name="lockable", level=logging.DEBUG):
    """
    Get lockable logger
    :return: Logger
    """
    # use default logger
    logger = logging.getLogger(name)
    handlers_len = len(logger.handlers)
    if handlers_len > 0:
        return logger

    if level is None:
        handler = logging.NullHandler()
    else:
        logger.setLevel(level)
        # create console handler and set level to debug
        handler = logging.StreamHandler()
        handler.setLevel(level)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        handler.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(handler)
    return logger
