'''
Created on Mar 17, 2014

@author: nathan

This class manages creating the client instances and forwarding messages
'''

import asyncio
import re
from sys import stderr
from contextlib import contextmanager, closing
from enum import Enum

from .client_sender import client_sender
from .body_util import make_body

me_is_pattern = re.compile(
    "^ME IS (?P<username>\w+)$")
send_pattern = re.compile(
    "^(?:(?P<send>SEND(?P<users>( \w+)+))|(?P<broadcast>BROADCAST))$")

short_pattern = '(?:$(?P<body_size>[0-9]{1,2})^)'
chunk_pattern = '(?:$C(?P<chunk_size>[0-9]{1,3})^)'

body_pattern = re.compile(
    "(?P<short>{short})|(?P<chunk>{chunk})".format(
        short=short_pattern, chunk=chunk_pattern))

short_pattern = re.compile(short_pattern)
chunk_pattern = re.compile(chunk_pattern)


class SendMode(Enum):
    send = 1
    broadcast = 2


class ChatManager:
    def __init__(self, randoms, verbosity, debug):
        self.chatters = {}
        self.randoms = [make_body(r) for r in randoms]
        self.verbose = verbosity
        self.debug = debug

        self.debug_print("Created chat manager with randoms:\n\t{randoms}".format(
            randoms='\n\t'.join(randoms)))

    def debug_print(self, *what):
        if(self.debug):
            print(*what, file=stderr)

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
        self.debug_print("Entering client context")
        if name in self.chatters:
            self.debug_print("Error: {name} already exists".format(name=name))
            writer.write('ERROR\n'.encode('ascii'))
            raise RuntimeError
        else:
            writer.write('OK\n'.encode('ascii'))

            try:
                self.debug_print("Adding {name} to chatters".format(name=name))
                self.chatters[name] = client_sender(writer, self.randoms)
                yield
            finally:
                self.debug_print("Removing {name} from chatters".format(name=name))
                del self.chatters[name]

    @asyncio.coroutine
    def client_connected(self, reader, writer):
        '''
        Primary client handler coroutine. One is spawned per client connection.
        '''
        # Ensure transport is closed at end
        with closing(writer):
            self.debug_print("Client connected")

            # Get the ME IS line
            line = yield from reader.readline()
            match = me_is_pattern.match(line.decode('ascii'))

            # Get the username
            if match is None:
                self.debug_print("Error reading ME IS line")
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
                        size = int(match.group('body_size'))

                        # Read body
                        body = yield from reader.readexactly(size)
                        body_parts.append(body)

                    elif match.lastgroup == 'chunk':
                        while True:
                            # Get chunk size
                            size = int(match.group('chunk_size'))

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
        self.debug_print("Launching server")
        # Need 1 server for each port
        servers = []
        for port in ports:
            self.debug_print("Listening on port", port)
            server = yield from asyncio.start_server(self.client_connected,
                None, port)
            servers.append(server.wait_closed())

        self.debug_print("Serving")
        yield from asyncio.wait(servers)
