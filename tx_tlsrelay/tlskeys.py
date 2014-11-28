import py
from twisted.internet import ssl
from twisted.protocols import tls
from twisted.internet import defer
from twisted.internet.endpoints import SSL4ClientEndpoint, SSL4ServerEndpoint, _WrappingFactory
from twisted.internet import interfaces
from zope.interface import implementer

@implementer(interfaces.IStreamClientEndpoint)
class SSL4ReverseServerEndpoint(object):
    def __init__(self, reactor, host, port, server_options,
            timeout=30, outgoing_bind_address=None):
        self._reactor = reactor
        self._host = host
        self._port = port
        self._server_options = server_options
        self._timeout = timeout
        self._bindAddress = outgoing_bind_address

    def connect(self, factory):
        tls_factory = tls.TLSMemoryBIOFactory(self._server_options,
                isClient=False, wrappedFactory=factory)
        try:
            wf = _WrappingFactory(tls_factory)
            self._reactor.connectTCP(
                self._host, self._port, wf,
                timeout=self._timeout, bindAddress=self._bindAddress)
            return wf._onConnection
        except:
            return defer.fail()


class TLSKeys(object):
    def __init__(self, reactor, basedir):
        self.reactor = reactor
        basedir = py.path.local(basedir)
        clientdata = (
            basedir.join("client.crt.pem").read_binary()
            + basedir.join("client.key.pem").read_binary()
        )
        serverdata = (
            basedir.join("server.crt.pem").read_binary()
            + basedir.join("server.key.pem").read_binary()
        )
        cadata = basedir.join("ca.crt.pem").read()
        self.server_cert = ssl.PrivateCertificate.loadPEM(serverdata)
        self.client_cert = ssl.PrivateCertificate.loadPEM(clientdata)
        self.ca_cert = ssl.Certificate.loadPEM(cadata)
        self.client_options = self.client_cert.options(self.ca_cert)
        self.server_options = self.server_cert.options(self.ca_cert)

    def server(self, port):
        return SSL4ServerEndpoint(self.reactor, port,
                self.server_options)

    def client(self, host, port):
        return SSL4ClientEndpoint(self.reactor, host, port,
                self.client_options)

    def reverse_server(self, host, port):
        return SSL4ReverseServerEndpoint(self.reactor, host, port,
                self.server_options)