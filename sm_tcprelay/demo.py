import argparse
import twisted

from sm_tcprelay.client import TCPRelayServerEndpoint

parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("host", default="127.0.0.1",
        help="the host to report to clients that is 'me'")
parser.add_argument("port", default=12000, type=int,
        help="port to listen for control connections")

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
    endpoint = TCPRelayServerEndpoint(args.host, args.port, reactor)
    d = endpoint.listen(factory)
    d.addCallback(connected)
    d.addErrback(print_and_shutdown)
    del d

    reactor.run()
