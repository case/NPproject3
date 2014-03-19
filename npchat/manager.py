'''
Created on Mar 17, 2014

@author: nathan

This class manages creating the client instances and forwarding messages
'''

import asyncio
import re
import contextlib
import random
from sys import stderr
from enum import Enum

from npchat import util

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


class NameExistsError(ChatError):
    '''
    Subclass of ChatError to enable that specific ERROR print in a non-extended
    protocol
    '''
    pass


class ChatManager:
    def __init__(self, randoms, random_rate, verbose, debug, extended):
        '''
        Initialize a chat manager

          `randoms`: the list of random phrases to inject
          `verbosity`: True for verbose output
          `debug`: True for debug output
          `random_rate`: How many normal messages to send between randoms
        '''
        self.chatters = {}
        self.random_rate = random_rate
        if random_rate:
            self.randoms = [b''.join(util.make_body(r)) for r in randoms]
        self.verbose = verbose
        self.debug = debug
        self.extended = extended

    @contextlib.contextmanager
    def login(self, name, writer):
        '''
        Attempt to login a username. Insert the client_sender into the chatters
        dictionary, and remove it when the context leaves. Raise a ChatError if
        name is already in the chatters dictionary
        '''
        # If name already exists, send error and throw
        if name in self.chatters:
            writer.write('ERROR\n'.encode('ascii'))
            raise ChatError("Name {name} already exists".format(name=name))

        # Create client sender
        @util.consumer
        def client_sender():
            '''
            Consumer-generator to handle sending messages to clients, and also
            injecting bonus messages
            '''
            # If we're using randoms
            if self.random_rate > 0 and self.randoms:
                while True:
                    # set would be better, but random.choice needs a sequence
                    recent = list()

                    # Perform random_rate normal writes, then a random write
                    for _ in range(self.random_rate):
                        sender, *body = yield
                        recent.append(sender)
                        writer.writelines(body)

                    writer.writelines([
                        util.make_sender_line(random.choice(recent)),
                        random.choice(self.randoms)])
            else:
                while True:
                    sender, *body = yield
                    writer.writelines(body)

        # Add sender to chatters
        self.chatters[name] = self.client_sender()

        # Write acknowledgment
        writer.write('OK\n'.encode('ascii'))

        # Enter context, and remove from dictionary when leaving
        try:
            yield
        finally:
            del self.chatters[name]

    @contextlib.contextmanager
    def handle_errors(self, writer):
        try:
            yield

        # Handle chat errors
        except ChatError as e:
            message = "ERROR: {e.message}\n".format(e=e).encode('ascii')
            # Debug Print
            if self.debug:
                stderr.write(message)

            # Inform client
            if self.extended:
                writer.write(message)

            # If we're not using extended, send normal error message
            elif isinstance(e, NameExistsError):
                writer.write(b"ERROR\n")

        # Handle other errors
        except Exception as e:
            if self.extended:
                writer.write('UNKNOWN SERVER ERROR\n'.encode('ascii'))
            raise

    @asyncio.coroutine
    def client_connected(self, reader, writer):
        '''
        Primary client handler coroutine. One is spawned per client connection.
        '''
        # Ensure transport is closed at end, and handle errors
        with contextlib.closing(writer), self.handle_errors(writer):

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

            # Parse the send line
            match = send_pattern.match(line.decode('ascii'))
            if match is None:
                raise ChatError("Malformed send line")

            elif match.lastgroup == 'send':
                mode = SendMode.send
                recipients = match.group('users').split()

            elif match.lastgroup == 'broadcast':
                mode = SendMode.broadcast

            else:
                raise ChatError("Unknown Server Error")

            # Get the first body header line
            line = yield from reader.readline()

            # Parse body header line
            match = body_pattern.match(line.decode('ascii'))
            if match is None:
                raise ChatError("Malformed body header")

            body_parts = [util.make_sender_line(name), line]

            # Read body
            if match.lastgroup == 'short':
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
                        raise ChatError("Malformed chunk header")

                    # Add chunk line to body
                    body_parts.append(line)
            else:
                raise ChatError("Unknown Server Error")

            # Construct the message for client_sender
            message = (name, ''.join(body_parts))

            # Send the message to a list of recipients
            if mode is SendMode.send:
                recipients = filter(lambda r: r in self.chatters, recipients)

            # Send the message to everyone (but ourselves)
            elif mode is SendMode.broadcast:
                recipients = filter(lambda r: name is not r, self.chatters)

            # Something went wrong with the mode?
            else:
                raise ChatError("Unknown Server Error")

            for recipient in recipients:
                self.chatters[recipient].send(message)

    @asyncio.coroutine
    def serve_forever(self, ports):

        servers = []
        for port in ports:
            # Need 1 server for each port
            # Start listening
            server = yield from asyncio.start_server(
                self.client_connected, None, port)

            # Get the listener task
            servers.append(server.wait_closed())

        yield from asyncio.wait(servers)
