'''
Created on Mar 17, 2014

@author: nathan
'''

import asyncio
from argparse import ArgumentParser
from npchat.manager import ChatManager

# TODO: more
default_randoms = (
    "Hey, you're kinda hot",
    "No way!",
    "I like Justin Bieber....a lot",
    "You butt",
    "GOOD",
    "I'm not touching yours, I'm only touching mine",
    "I want you to lose so hard you go inactive",
    "Philadelphia is the worst state in the world",
    "BIG\tBLACK\tDICK",
    "i'm all about three things, getting money, getting pussy, and the dewey "
        "decimal system")


def main():
    parser = ArgumentParser(
        description="Network Programming Project 3: Chat Server")

    parser.add_argument('-v', "--verbose", action='store_true',
        help="Enable standard verbose output")
    parser.add_argument('-d', "--debug", action='store_true',
        help="Print additional status messages")
    parser.add_argument('-e', "--extra", action='append', dest='randoms',
        help="Additional random phrases to inject", metavar='MESSAGE',
        default=[])
    parser.add_argument('-r', '--rate', type=int, default=3,
        help="How many normal messages to send between random messages "
        "(default: 3)", dest='random_rate')
    parser.add_argument('-x', '--extended', action='store_true',
        help="Use Nathan's protocol extensions")
    parser.add_argument('-E', '--exclude', action='store_false',
        help="Exclude the build-in random messages", dest='use_default')
    parser.add_argument("ports", nargs='+', type=int, metavar='PORT',
        help="TCP/UDP port(s) to listen on")

    args = parser.parse_args()
    if args.use_default:
        args.randoms.extend(default_randoms)
    chat_manager = ChatManager(args.randoms, args.random_rate, args.verbose,
        args.debug, args.extended)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(chat_manager.serve_forever(args.ports))

if __name__ == '__main__':
    main()
