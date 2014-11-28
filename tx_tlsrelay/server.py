# This file is licensed MIT. see license.txt.

# note: usually I'd translate twisted's parlance of
# "factory" and "protocol" to "server" and "session",
# but in this case there are so many servers and clients
# immediately adjacent that it got too confusing to user
# "server". I kept "session", though.

# note: this program contains refloops. I left those up to
# the gc of <your interpreter here> to deal with.

# note: this program doesn't make the SLIGHTEST ATTEMPT at
# authentication. it's left up to the application protocol
# to implement any such thing (ssl, for instance). DO NOT
# BLINDLY TRUST THE RELAY'S SAFETY.

# note: this program does not differentiate connections by
# any sort of ID, due to not having any way to notify the
# reverse client of what the connection's ID is on connect
# (since it's intended to be an extra-vanilla protocol for
# reverse-connecting side).

# note: this program is ipv4-only.

from collections import deque
import argparse

from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import LineOnlyReceiver


class ChildSession(Protocol):
    def connectionMade(self):
        self.transport.setTcpKeepAlive(True)

        if self.control_session is None:
            self.transport.write("no controller linked")
            self.transport.loseConnection()
            return

        # yay inheritance
        self.finish_setup()
        self.factory.sessions.append(self)

    def connectionLost(self, reason):
        self.pre_deinit()
        try:
            self.factory.sessions.remove(self)
        except ValueError:
            pass


class PublicSession(ChildSession):
    def __init__(self):
        self.queue = deque()
        self.reverse_session = None
        self.disconnected = False

    def finish_setup(self):
        self.control_session.public_ready(self)

    def dataReceived(self, data):
        # DOS vulnerability: connect to control session; connect to public
        # port; send lots of data without connecting to reverse port to
        # receive it.
        if not self.reverse_session:
            self.queue.append(data)
        else:
            self.reverse_session.transport.write(data)

    def pre_deinit(self):
        if self.reverse_session:
            self.reverse_session.transport.loseConnection()
        self.disconnected = True


class ReverseSession(ChildSession):
    def __init__(self):
        self.public_session = None

    def finish_setup(self):
        try:
            self.public_session = self.control_session.queue.popleft()
        except IndexError:
            # TODO: report to controller client that it made an
            # extra connection?
            self.transport.loseConnection()
            return
        self.public_session.reverse_session = self
        for data in self.public_session.queue:
            self.transport.write(data)
        if self.public_session.disconnected:
            self.transport.loseConnection()

    def dataReceived(self, data):
        self.public_session.transport.write(data)

    def pre_deinit(self):
        if self.public_session:
            self.public_session.transport.loseConnection()


class ChildFactory(Factory):
    def __init__(self):
        self.sessions = []
        self.control_session = None
        self.address = None

    def killall(self):
        for session in self.sessions:
            session.transport.loseConnection()

    def buildProtocol(self, addr):
        p = Factory.buildProtocol(self, addr)
        p.control_session = self.control_session
        return p


class ControlSession(LineOnlyReceiver):
    def __init__(self):
        self.reverse = None
        self.public = None
        self.queue = deque()

    def connectionMade(self):
        self.transport.setTcpKeepAlive(True)

        if not self.factory.reverse_factories:
            self.sendLine("no_available_listeners")
            self.transport.loseConnection()
            return

        self.reverse = self.factory.reverse_factories.popleft()
        self.public = self.factory.public_factories.popleft()
        self.reverse.control_session = self
        self.public.control_session = self

        self.sendLine("public_listener " + self.public.address)
        self.sendLine("reverse_listener " + self.reverse.address)

    def connectionLost(self, reason):
        if not self.public:
            return

        # connections will linger for a moment, but new ones
        # will be set up correctly, so that's okay
        self.reverse.killall()
        self.public.killall()

        self.reverse.control_session = None
        self.public.control_session = None

        self.factory.reverse_factories.append(self.reverse)
        self.factory.public_factories.append(self.public)

    def public_ready(self, public_session):
        self.queue.append(public_session)
        self.sendLine("new_connection")


class ControlFactory(Factory):
    protocol = ControlSession

    def __init__(self, port_count):
        self.reverse_factories = deque()
        self.public_factories = deque()
        for _ in range(port_count / 2):
            reverse = ChildFactory.forProtocol(ReverseSession)
            public = ChildFactory.forProtocol(PublicSession)
            self.reverse_factories.append(reverse)
            self.public_factories.append(public)

        self.all_child_factories = (list(self.reverse_factories) +
                                    list(self.public_factories))


def even_int(v): # pragma: no cover
    x = int(v)
    if x % 2 != 0:
        raise ValueError("must be divisible by 2")
    return x


parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("port", nargs="?", default=12000, type=int,
        help="port to listen for control connections")
parser.add_argument("--port-count", default=200, type=even_int,
        help="how many ports above --port to allocate for relaying")
parser.add_argument("--myhost", default="127.0.0.1",
        help="the host to report to clients that is 'me'")


def main():
    args = parser.parse_args()

    from twisted.internet import reactor
    control = ControlFactory(args.port_count)

    reactor.listenTCP(args.port, control)
    for index, child_factory in enumerate(control.all_child_factories):
        port = index + 1 + args.port
        child_factory.address = "%s:%d" % (args.myhost, port)
        reactor.listenTCP(port, child_factory)

    reactor.run()
