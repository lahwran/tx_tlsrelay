#!/usr/bin/env python
from setuptools import setup, find_packages


vers = "2.1.1"

setup(
        name="tx_tlsrelay",
        description="A simple relay. See readme.md",
        version=vers,
        packages=find_packages(),
        license='MIT',
        author="lahwran",
        author_email="lahwran0@gmail.com",
        url="https://github.com/lahwran/tx_tlsrelay",
        download_url="https://github.com/lahwran/tx_tlsrelay/tarball/" + vers,
        scripts=["bin/tx_tlsrelay"],
        install_requires=[
            "Twisted>=14.0.2",
            "coverage>=3.7.1",
            "cryptography>=0.6.1",
            "py>=1.4.26",
            "pyOpenSSL>=0.14",
            "service-identity>=14.0.0",
        ],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Framework :: Twisted',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Natural Language :: English',
            'Operating System :: POSIX',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 2 :: Only',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python :: Implementation :: CPython',
            'Topic :: Communications',
            'Topic :: Internet',
            'Topic :: System :: Distributed Computing',
            'Topic :: System :: Networking',
        ]
)
