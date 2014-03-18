'''
Created on Mar 17, 2014

@author: nathan

This class manages creating the client instances and forwarding messages
'''

import asyncio
import re
from contextlib import contextmanager
from enum import Enum

from .client_sender import client_sender

me_is_pattern = re.compile(
    "^ME IS (?P<username>\w+)$")
send_pattern = re.compile(
    "^(?:(?P<send>SEND(?P<users>( \w+)+))|(?P<broadcast>BROADCAST))$")

short_pattern = '(?:$(?P<size>[0-9]{1,2})^)'
chunk_pattern = '(?:$C(?P<size>[0-9]{1,3})^)'

body_pattern = re.compile(
    "(?P<short>{short})|(?P<chunk>{chunk})".format(
        short=short_pattern, chunk=chunk_pattern))

short_pattern = re.compile(short_pattern)
chunk_pattern = re.compile(chunk_pattern)


class SendMode(Enum):
    send = 1
    broadcast = 2


class ChatManager:
    def __init__(self, randoms):
        self.chatters = {}
        self.randoms = randoms

    def send_message(self, sender, recipient, body_parts):
        try:
            self.chatters[recipient].send((sender, body_parts))
        except KeyError as e:
            raise RuntimeError from e

    @contextmanager
    def client_context(self, name, writer):
        '''
        Create a client context. Insert the client_sender into the chatters
        dictionary, and remove it when the context leaves.
        '''
        if name in self.chatters:
            raise RuntimeError
        self.chatters[name] = client_sender(writer, self.randoms)

        try:
            yield
        finally:
            del self.chatters[name]

    @asyncio.coroutine
    def client_connected(self, reader, writer):
        '''
        Primary client handler coroutine. One is spawned per client connection.
        '''
        # Get the ME IS line
        line = yield from reader.readline()
        match = me_is_pattern.match(line.decode('ascii'))

        # Get the username
        if match is None:
            raise RuntimeError()  # TODO: error message
        name = match.group('username')

        # Add self to the client list, and remove when done
        with self.client_context(name, writer):
            while True:
                # Get the send line (SEND name name / BROADCAST)
                line = yield from reader.readline()

                # If no data was recieved, assume connection was closed
                if not line:
                    break
                # TODO: find out if asyncio has a better way to detect this

                match = send_pattern.match(line.decode('ascii'))

                # Parse the send line
                if match is None:
                    raise RuntimeError()  # TODO: add error message
                elif match.lastgroup == 'send':
                    mode = SendMode.send
                    recipients = match.group('users').split()
                elif match.lastgroup == 'broadcast':
                    mode = SendMode.broadcast
                else:
                    raise RuntimeError()

                # Get the first body header line
                line = yield from reader.readline()
                match = body_pattern.match(line.decode('ascii'))

                body_parts = [line]

                if match is None:
                    raise RuntimeError()  # TODO: add error message
                elif match.lastgroup == 'short':
                    # Get body size
                    size = int(match.group('size'))

                    # Read body
                    body = yield from reader.readexactly(size)
                    body_parts.append(body)

                elif match.lastgroup == 'chunk':
                    while True:
                        # Get chunk size
                        size = int(match.group('size'))

                        # Break on chunk size of 0
                        if size == 0:
                            break

                        # Read chunk
                        chunk = yield from reader.readexactly(size)
                        body_parts.append(chunk)

                        # Get next chunk line
                        line = yield from reader.readline()
                        match = chunk_pattern.match(line.decode('ascii'))
                        if match is None:
                            raise RuntimeError()

                        # Add chunk line to body
                        body_parts.append(line)
                else:
                    raise RuntimeError()

                message = (name, body_parts)

                # Send the message to a list of recipients
                if mode is SendMode.send:
                    if any(r not in self.chatters for r in recipients):
                        raise RuntimeError()

                    for recipient in recipients:
                        self.chatters[recipient].send(message)

                # Send the message to everyone (but ourselves)
                elif mode is SendMode.broadcast:
                    for recipient, send_func in self.chatters.items():
                        if recipient is not name:
                            send_func.send(message)

                # Something went wrong with the mode?
                else:
                    raise RuntimeError

    @asyncio.coroutine
    def serve_forever(self, ports):
        # Need 1 server for each port
        servers = [(yield from asyncio.start_server(self.client_connected,
            None, port)) for port in ports]

        yield from asyncio.wait(servers)
