'''
Created on Mar 17, 2014

@author: nathan

This class manages creating the client instances and forwarding messages
'''

import asyncio
import re
import contextlib
from sys import stderr
from enum import Enum

from .client_sender import client_sender
from .body_util import make_body

me_is_pattern = re.compile(
    "^ME IS (?P<username>\w+)$",
    re.IGNORECASE)
send_pattern = re.compile(
    "^(?:(?P<send>SEND(?P<users>( \w+)+))|(?P<broadcast>BROADCAST))$",
    re.IGNORECASE)

short_pattern = '(?P<body_size>[0-9]{1,2})'
chunk_pattern = 'C(?P<chunk_size>[0-9]{1,3})'

body_pattern = re.compile(
    "^(?:(?P<short>{short})|(?P<chunk>{chunk}))$".format(
        short=short_pattern, chunk=chunk_pattern),
    re.IGNORECASE)

short_pattern = re.compile(
    "^{short}$".format(short=short_pattern),
    re.IGNORECASE)
chunk_pattern = re.compile(
    "^{chunk}$".format(chunk=chunk_pattern),
    re.IGNORECASE)


class SendMode(Enum):
    send = 1
    broadcast = 2


class ChatError(RuntimeError):
    @property
    def message(self):
        return self.args[0]


class ChatManager:
    def __init__(self, randoms, verbosity, debug):
        self.chatters = {}
        self.randoms = [b''.join(make_body(r)) for r in randoms]
        self.verbose = verbosity
        self.debug = debug

        self.debug_print(
            "Created chat manager with randoms:\n\t{randoms}".format(
                randoms='\n\t'.join(randoms)))

    def debug_print(self, *what):
        if(self.debug):
            print(*what, file=stderr)

    @contextlib.contextmanager
    def client_context(self, name, writer):
        '''
        Create a client context. Insert the client_sender into the chatters
        dictionary, and remove it when the context leaves. Raise a ChatError if
        name is already in the chatters dictionary
        '''
        # If name already exists, send error and throw
        if name in self.chatters:
            writer.write('ERROR\n'.encode('ascii'))
            raise ChatError("Name {name} already exiists".format(name=name))

        # Add to dictionary and enter context
        try:
            # Add to dictionary
            self.debug_print("Adding {name} to chatters".format(name=name))
            self.chatters[name] = client_sender(writer, self.randoms)

            # Send acknowledgment
            writer.write('OK\n'.encode('ascii'))

            # Enter context
            yield
        finally:
            # When leaving the context, remove from dictionary
            self.debug_print("Removing {name} from chatters".format(name=name))
            del self.chatters[name]

    @contextlib.contextmanager
    def handle_chat_errors(self, handle=True):
        '''
        Context manager to catch ChatErrors and debug_print the message. If
        handle is False, they are reraised, allowing complete tracebacks
        '''
        try:
            yield
        except ChatError as e:
            if handle:
                self.debug_print("Error: {e.message}".format(e=e))
            else:
                raise

    @asyncio.coroutine
    def client_connected(self, reader, writer):
        '''
        Primary client handler coroutine. One is spawned per client connection.
        '''
        # Ensure transport is closed at end, and print ChatErrors
        with self.handle_chat_errors(), contextlib.closing(writer):
            self.debug_print("Client connected")

            # Get the ME IS line
            line = yield from reader.readline()
            match = me_is_pattern.match(line.decode('ascii'))

            # Get the username
            if match is None:
                raise ChatError("Malformed ME IS line")

            name = match.group('username')

            # Add self to the client list, and remove when done
            with self.client_context(name, writer):
                yield from self.core_loop(name, reader)

    @asyncio.coroutine
    def core_loop(self, name, reader):
        '''
        This coroutine handles serving messages, after all the initial
        handshaking and context stuff is set up.
        '''
        while True:
            # Get the send line (SEND name name / BROADCAST)
            line = yield from reader.readline()

            # If no data was received, assume connection was closed
            if not line:
                break
            # TODO: find out if asyncio has a better way to detect this

            match = send_pattern.match(line.decode('ascii'))

            # Parse the send line
            if match is None:
                raise ChatError("Malformed send line")

            elif match.lastgroup == 'send':
                mode = SendMode.send
                recipients = match.group('users').split()
                self.debug_print("Got SEND line\n\t{recipients}".format(
                    recipients='\n\t'.join(recipients)))

            elif match.lastgroup == 'broadcast':
                self.debug_print("Got BROADCAST line")
                mode = SendMode.broadcast

            else:
                raise ChatError("Unknown Server Error")

            # Get the first body header line
            line = yield from reader.readline()
            match = body_pattern.match(line.decode('ascii'))

            body_parts = [line]

            if match is None:
                raise ChatError("Malformed body header")

            elif match.lastgroup == 'short':
                # Get body size
                size = int(match.group('body_size'))
                self.debug_print(
                    "Reading body of size {size}".format(size=size))

                # Read body
                body = yield from reader.readexactly(size)
                body_parts.append(body)

            elif match.lastgroup == 'chunk':
                while True:
                    # Get chunk size
                    size = int(match.group('chunk_size'))
                    self.debug_print(
                        "Reading chunk of size {size}".format(size=size))

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
                        raise ChatError("Malformed chunk header")

                    # Add chunk line to body
                    body_parts.append(line)
            else:
                raise ChatError("Unknown Server Error")

            # Construct the message for client_sender
            message = (name, body_parts)

            # Send the message to a list of recipients
            if mode is SendMode.send:
                recipients = (r for r in recipients if r in self.chatters)

            # Send the message to everyone (but ourselves)
            elif mode is SendMode.broadcast:
                recipients = (r for r in self.chatters if name is not r)

            # Something went wrong with the mode?
            else:
                raise ChatError("Unknown Server Error")

            for recipient in recipients:
                self.chatters[recipient].send(message)
                self.debug_print(
                    "Sent to {recipient}".format(recipient=recipient))

    @asyncio.coroutine
    def serve_forever(self, ports):
        self.debug_print("Launching server")

        servers = []
        for port in ports:
            # Need 1 server for each port
            self.debug_print("Listening on port", port)
            server = yield from asyncio.start_server(
                self.client_connected, None, port)
            servers.append(server.wait_closed())

        self.debug_print("Serving")
        yield from asyncio.wait(servers)
