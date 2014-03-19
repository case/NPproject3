'''
Created on Mar 17, 2014

@author: nathan
'''

import asyncio
from argparse import ArgumentParser
from pychat.manager import ChatManager

# TODO: more
initial_randoms = [
    "Hey, you're kinda hot",
    "No way!",
    "I like Justin Bieber....a lot"]


def main():
    parser = ArgumentParser(
        description="Network Programming Project 3: Chat Server")
    parser.add_argument('-v', "--verbose", action='store_true',
        help='Enable standard verbose output')
    parser.add_argument('-d', "--debug", action='store_true',
        help="Print additional status messages")
    parser.add_argument('-e', "--extra", action='append', dest='randoms',
        metavar='phrase', help="Additional random phrases to inject",
        default=[])
    parser.add_argument('-r', '--rate', type=int, default=3,
        help="How many normal messages to send between random messages",
        dest='random_rate')
    parser.add_argument('-D', '--exclude-default', action='store_false',
        help="Exclude the build-in random messages", dest='use_default')
    parser.add_argument("ports", nargs='+', type=int, metavar='port',
        help="TCP/UDP port to listen on")

    args = parser.parse_args()

    if args.use_default:
        args.randoms.extend(initial_randoms)

    chat_manager = ChatManager(args.randoms, args.verbose, args.debug,
        args.random_rate)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(chat_manager.serve_forever(args.ports))

if __name__ == '__main__':
    main()
