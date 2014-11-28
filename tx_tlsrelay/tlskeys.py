import py
from twisted.internet import ssl
from twisted.internet.endpoints import SSL4ClientEndpoint, SSL4ServerEndpoint

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
