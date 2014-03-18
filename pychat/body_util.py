'''
Created on Mar 18, 2014

@author: nathan
'''


def make_sender_line(name):
    return 'FROM {name}\n'.format(name=name).encode('ascii')


def make_body(body):
    body = body.encode('ascii')
    if len(body) <= 99:
        yield '{size}\n'.format(size=len(body)).encode('ascii')
        yield body
    else:
        # TODO: chunked encoding
        raise NotImplementedError
