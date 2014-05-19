# note: usually I'd translate twisted's parlance of
# "factory" and "protocol" to "server" and "session",
# but in this case there are so many servers and clients
# immediately adjacent that it got too confusing to user
# "server". I kept "session", though.
# note: this program contains refloops. I left those up to
# the gc of <your interpreter here> to deal with.

from collections import deque

from sm_tcprelay import tokens

from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import LineOnlyReceiver


class ChildSession(Protocol):
    def connectionMade(self):
        self.transport.setTcpKeepAlive(True)

        if self.control_session is None:
            self.transport.write(tokens.NOT_LINKED)
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

    def finish_setup(self):
        self.control_session.public_ready(self)

    def dataReceived(self, data):
        # DOS vulnerability: connect to control session; connect to public
        # port; send lots of data without connecting to reverse port to
        # receive it
        if not self.reverse_session:
            self.queue.append(data)
        else:
            self.reverse_session.transport.write(data)

    def pre_deinit(self):
        if self.reverse_session:
            self.reverse_session.transport.loseConnection()
        if self.control_session:
            try:
                self.control_session.queue.remove(self)
            except ValueError:
                pass
            self.control_session.sendLine(tokens.EXPECT_DISCONNECT)


class ReverseSession(ChildSession):
    def __init__(self):
        self.public_session = None

    def finish_setup(self):
        try:
            self.public_session = self.control_session.queue.popleft()
        except IndexError:
            self.control_session.sendLine(tokens.NO_MORE_CONNECTIONS)
            self.transport.loseConnection()
            return
        self.public_session.reverse_session = self
        for data in self.public_session.queue:
            self.transport.write(data)

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
            self.sendLine(tokens.NO_AVAILABLE_LISTENERS)
            self.transport.loseConnection()
            return

        self.reverse = self.factory.reverse_factories.popleft()
        self.public = self.factory.public_factories.popleft()
        self.reverse.control_session = self
        self.public.control_session = self

        self.sendLine(tokens.YOUR_PUBLIC_LISTENER_IS + self.public.address)
        self.sendLine(tokens.YOUR_REVERSE_LISTENER_IS + self.reverse.address)

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
        self.sendLine(tokens.NEW_CONNECTION_READY)


class ControlFactory(Factory):
    protocol = ControlSession

    def __init__(self):
        self.reverse_factories = deque()
        self.public_factories = deque()
        for _ in range(PORT_COUNT / 2):
            reverse = ChildFactory.forProtocol(ReverseSession)
            public = ChildFactory.forProtocol(PublicSession)
            self.reverse_factories.append(reverse)
            self.public_factories.append(public)

        self.all_child_factories = (list(self.reverse_factories) +
                                    list(self.public_factories))


# pretend these constants are in a config file
# - hostname to announce to clients
MYHOSTNAME = "127.0.0.1"
# - control port
PORT_BASE = 12000
PORT_COUNT = 200
assert PORT_COUNT % 2 == 0, ("as there are two ports for each service,"
        " port count must be divisible by 2")

control = ControlFactory()
reactor.listenTCP(PORT_BASE, control)
for index, child_factory in enumerate(control.all_child_factories):
    port = index + 1 + PORT_BASE
    child_factory.address = "%s:%d" % (MYHOSTNAME, port)
    reactor.listenTCP(port, child_factory)

reactor.run()
