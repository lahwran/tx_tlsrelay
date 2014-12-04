# This file is licensed MIT. see license.txt.

import argparse
import twisted
import py

from tx_tlsrelay.tlskeys import TLSKeys

parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("host", default="127.0.0.1",
        help="the host to report to clients that is 'me'")
parser.add_argument("port", default=12000, type=int,
        help="port to listen for control connections")
parser.add_argument("-a", "--application-certs", type=py.path.local,
        default="./application_certs")
parser.add_argument("-c", "--relay-certs", type=py.path.local,
        default="./relay_client_certs")

def demo(factory):
    args = parser.parse_args()

    def connected(listener):
        print listener.getHost()


    def print_and_shutdown(error):
        try:
            reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            pass
        return error

    from twisted.internet import reactor

    relay_keys = TLSKeys(reactor, args.relay_certs)
    application_keys = TLSKeys(reactor, args.application_certs)

    relay_client = relay_keys.client(args.host, args.port)
    server = application_keys.relayed_server(relay_client)

    d = server.listen(factory)
    d.addCallback(connected)
    d.addErrback(print_and_shutdown)
    del d

    reactor.run()
