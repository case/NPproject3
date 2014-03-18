'''
Created on Mar 17, 2014

@author: nathan

ClientSender class handles sending messages to a client. It's primarily
responsible for message injection.
'''

import random
from functools import wraps

from .body_util import make_sender_line


def consumer(func):
    '''
    Immediately advance a generator to the first yield.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        f = func(*args, **kwargs)
        next(f)
        return f
    return wrapper

# TODO: verbosity prints
@consumer
def client_sender(writer, randoms):
    '''
    Consumer-generator to handle writing messages to the client. Handles
    prepending the 'FROM' string and injecting random messages every so often.
    '''
    while True:
        recent_writers = set()

        # Perform 3 normal writes, then a random write
        for _ in range(3):
            sender, body_parts = yield
            sender_line = make_sender_line(sender)
            recent_writers.add(sender_line)
            writer.write(sender_line)
            writer.writelines(body_parts)

        writer.writelines([
            random.choice(list(recent_writers)),
            random.choice(randoms)])
