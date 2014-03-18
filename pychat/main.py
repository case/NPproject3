'''
Created on Mar 17, 2014

@author: nathan
'''

import asyncio
from argparse import ArgumentParser
from .manager import ChatManager

# TODO: more
randoms = [
    "Hey, you're kinda hot",
    "No way!",
    "I like Justin Bieber....a lot"]


def main():
    parser = ArgumentParser(
        description="Network Programming Project 3: Chat Server")
    parser.add_argument('-v', "--verbose", action='store_true',
        dest='verbosity')
    parser.add_argument('-d', "--debug", action='store_true',
        help="Print additional status messages")
    parser.add_argument('-e', "--extra", action='append', default=randoms,
        dest='randoms', metavar='phrase',
        help="Additional random phrases to inject")
    parser.add_argument("ports", nargs='+', type=int, metavar='port',
        help="TCP/UDP port to listen on")

    args = parser.parse_args()

    # TODO: verbose output
    chat_manager = ChatManager(args.randoms, args.verbosity)

    asyncio.get_event_loop().run_until_complete(asyncio.Task(
        chat_manager.serve_forever(args.ports)))

if __name__ == '__main__':
    main()
