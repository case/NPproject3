'''
Created on Mar 17, 2014

@author: nathan
'''

import asyncio
from argparse import ArgumentParser
from .manager import ChatManager
from .body_util import make_body

# TODO: more
randoms = [
    "Hey, you're kinda hot",
    "No way!",
    "I like Justin Bieber....a lot"]


def main():
    parser = ArgumentParser(
        description="Network Programming Project 3: Chat Server")
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument('-e', "--extra", action='append', default=randoms,
        dest='randoms')
    parser.add_argument("port", nargs='+', type=int, dest='ports',
        help="TCP/UDP port to listen on")

    args = parser.parse_args()

    # TODO: verbose output
    chat_manager = ChatManager([make_body(r) for r in args.randoms])

    asyncio.get_event_loop().run_until_complete(
        chat_manager.serve_forever(args.ports))
