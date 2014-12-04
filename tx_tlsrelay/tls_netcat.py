# connect to server
# read from stdin, write to server
# read from server, write to stdout

import argparse
import py
import sys
from twisted.internet import process
from twisted.internet import protocol
import twisted

from tx_tlsrelay.tlskeys import TLSKeys

def debug(msg):
    return
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.stderr.flush()

class Netcat(protocol.Protocol):
    def __init__(self, reactor):
        self.reactor = reactor

    def connectionMade(self):
        debug("outgoing connection made")
        self.reader = process.ProcessReader(self.reactor, self, "in", 0)

    def dataReceived(self, data):
        debug("got data: %r" % (data,))
        sys.stdout.write(data)
        sys.stdout.flush()

    def childDataReceived(self, fd, data):
        debug("got stdin data: %r" % (data,))
        self.transport.write(data)

    def connectionLost(self, reason):
        debug("outgoing connection lost: %r" % (reason,))
        try:
            self.reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            pass

    def childConnectionLost(self, fd, reason):
        debug("stdin connection lost: %r" % (reason,))
        try:
            self.reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    parser.add_argument("-k", "--tls-directory",
            type=py.path.local, required=True)
    parser.add_argument("-r", "--reverse-server", action="store_true")
    try:
        args = parser.parse_args()
    except:
        print sys.argv
        raise

    from twisted.internet import reactor

    def print_and_shutdown(error):
        error.printBriefTraceback()
        try:
            reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            pass

    tls_keys = TLSKeys(reactor, args.tls_directory)

    if args.reverse_server:
        endpoint = tls_keys.reverse_server(args.host, args.port)
    else:
        endpoint = tls_keys.client(args.host, args.port)

    d = endpoint.connect(protocol.Factory.forProtocol(lambda *a, **kw: Netcat(reactor)))
    d.addErrback(print_and_shutdown)
    del d

    reactor.run()

if __name__ == "__main__":
    main()
