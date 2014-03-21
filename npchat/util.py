'''
Created on Mar 18, 2014

@author: nathan
'''

from functools import wraps

SHORT_SIZE = 99
CHUNK_SIZE = 999


def make_sender_line(name):
    '''
    Create a formatted, encoded sender line
    '''
    return 'FROM {name}\n'.format(name=name).encode('ascii')


def make_body(*body):
    '''
    Create an encoded body, with correct length prefixing
    '''
    body = ''.join(body).encode('ascii')
    if len(body) <= SHORT_SIZE:
        yield '{size}\n'.format(size=len(body)).encode('ascii')
        yield body
    else:
        # Prevent unnecessary copies with memoryview.
        # Look, kids! Python can do arrays via pointer manipulation, too!
        body = memoryview(body)
        for i in range(0, len(body), CHUNK_SIZE):
            chunk = body[i:i + CHUNK_SIZE]
            yield 'C{size}\n'.format(size=len(chunk)).encode('ascii')
            yield chunk
        yield 'C0\n'.encode('ascii')


def assemble_full_body(sender_line, body_parts):
    '''
    Concatenate a sender line and body. Performs no formatting. Designed to be
    used with make_sender_line and make_body.
    '''
    yield sender_line
    yield from body_parts


def prepare_full_body(name, body_parts):
    '''
    Add a sender line to some body parts. Designed to be used with just
    make_body
    '''
    return assemble_full_body(make_sender_line(name), body_parts)


def make_full_body(name, *body):
    '''
    Encode a sender line and body.
    '''
    return prepare_full_body(name, make_body(*body))


def consumer(generator):
    '''
    Immediately advance a generator to the first yield. Attach to generators
    that consume data via send.
    '''
    @wraps(generator)
    def wrapper(*args, **kwargs):
        g = generator(*args, **kwargs)
        next(g)
        return g
    return wrapper
