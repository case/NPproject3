'''
Created on Mar 18, 2014

@author: nathan
'''

from setuptools import setup

setup(
    name="pychat",
    version="0.1.0",
    packages=['pychat'],
    # test_suite='test',
    platforms='any',

    author="Nathan West",
    description="A simple chat server",
    license="MIT",
    url="https://github.com/Lucretiel/NPproject3",

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: asyncio',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Communications',
        'Topic :: Communications :: Chat',
        'Topic :: Internet',
    ],

    entry_points={
        'console_scripts': [
            'chat_server = pychat.main:main'
        ]
    }
)
