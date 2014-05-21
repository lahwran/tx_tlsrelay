# note: this program is ipv4-only.

from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet.defer import Deferred
from twisted.internet.error import CannotListenError
from twisted.internet.protocol import Factory
from twisted.internet import address
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet import interfaces
from zope.interface import implementer


class RelayFullError(CannotListenError):
    def __init__(self):
        pass

    def __str__(self):
        return "RelayFullError()"


class Address(address._IPAddress):
    def __repr__(self):
        return super(self, Address).__str__()

    def __str__(self):
        return "%s:%d" % (self.host, self.port)

@implementer(interfaces.IListeningPort)
class ControlClient(LineOnlyReceiver):
    def __init__(self, reactor, childfactory):
        self.reactor = reactor
        self.childfactory = childfactory
        self.expected_count = 0
        self.public_address = None
        self.reverse_address = None
        self.reverse_endpoint = None
        self.listening_deferred = Deferred()
        self.disconnect_deferred = Deferred()

        self.childfactory.doStart()

    def lineReceived(self, line):
        message, _, tail = line.partition(" ")
        handler = getattr(self, "message_" + message, None)
        if handler is None:  # pragma: no cover
            print "unknown message", message, tail
            return
        handler(tail)

    def message_new_connection(self, tail):
        self.reverse_endpoint.connect(self.childfactory)

    def message_no_available_listeners(self, tail):
        self.listening_deferred.errback(RelayFullError())
        self.transport.loseConnection()

    def _splitaddress(self, text):
        host, _, port = text.rpartition(":")
        port = int(port)
        return Address("TCP", host, port)

    def message_public_listener(self, tail):
        self.public_address = self._splitaddress(tail)
        if self.reverse_address:  # pragma: no cover
            self.listening_deferred.callback(self)

    def message_reverse_listener(self, tail):
        self.reverse_address = addr = self._splitaddress(tail)
        self.reverse_endpoint = TCP4ClientEndpoint(self.reactor,
                                                    addr.host, addr.port)
        if self.public_address:
            self.listening_deferred.callback(self)

    def connectionLost(self, reason):
        self.childfactory.doStop()
        self.disconnect_deferred.callback(self)

    # IListeningPort functions

    def startListening(self):
        pass

    def stopListening(self):
        self.transport.loseConnection()
        return self.disconnect_deferred

    def getHost(self):
        return self.public_address


class ControlClientFactory(Factory):
    def __init__(self, protocol):
        self.protocol = protocol

    def buildProtocol(self, addr):
        return self.protocol


@implementer(interfaces.IStreamServerEndpoint)
class TCPRelayServerEndpoint(object):
    def __init__(self, host, port, reactor=None):
        if reactor is None:
            from twisted.internet import reactor
        self.reactor = reactor

        self.relayendpoint = TCP4ClientEndpoint(reactor,
                host, port)

    def listen(self, childfactory):

        protocol = ControlClient(self.reactor, childfactory)
        factory = ControlClientFactory(protocol)
        connect_defer = self.relayendpoint.connect(factory)

        @connect_defer.addCallback
        def chain(ignored_val):
            return protocol.listening_deferred

        return connect_defer
