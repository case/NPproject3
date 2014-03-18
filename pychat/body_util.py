'''
Created on Mar 18, 2014

@author: nathan
'''

from itertools import count

SHORT_SIZE = 99
CHUNK_SIZE = 999


def make_sender_line(name):
    '''
    Create a formatted, encoded sender line
    '''
    return 'FROM {name}\n'.format(name=name).encode('ascii')


def make_body(body):
    '''
    Create an encoded body, with correct length prefixing
    '''
    body = body.encode('ascii')
    if len(body) <= SHORT_SIZE:
        yield '{size}\n'.format(size=len(body)).encode('ascii')
        yield body
    else:
        body = memoryview(body)
        for i in count(0, CHUNK_SIZE):
            chunk = body[i:i + CHUNK_SIZE]
            yield 'C{size}\n'.format(size=len(chunk)).encode('ascii')
            yield chunk
        yield b'C0'
