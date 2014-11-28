Cheapo TCP/TLS Relay
====================

This was originally written as part of my interviewing process for the company I
currently work at (as of the commit that edits this line). As it was written before
I signed anything with that company, I own the copyright (verified with my boss).

I'm releasing it under the MIT license. see license.txt.

Explanation
-----------

First, lingo:

- "server" means a program using the relay to provide a service
- "client" means a program connecting to the relay to use a service
- "relay" means the relay server itself; "server" will not be used to refer to this


Implementation and Protocol
---------------------------

The relay uses a very cheap approach: for each incoming connection, the server must
initiate a new TCP/TLS connection to the relay. This has all the drawbacks associated
with creating a new TCP/TLS connection, but means that you don't have to write a
multiplexer-protocol implementation to use it.

On startup, the relay allocates a pool of listening ports. This is done ahead of time
to ensure that the frequent allocation and release of ports does not allow other
processes on the system to grab ownership of the ports. The number of ports the relay
allocates is configurable via --port-count, and must be divisible by 2, as the relay
assigns two ports to each server: a public port and a reverse port.

Other notes: the relay only supports ipv4 (it wouldn't be too hard to add ipv6, but
I didn't bother). Also, the relay doesn't have any way to differentiate connections.
However, as long as you don't write bugs and nobody tries to mess you up, everything
will work fine. Nothing to worry about. It'll be fine. Stop asking questions.

Usage
-----

Quick version:

1. start `bin/tx_tlsrelay`. defaults to port 12000, or takes port on command line;
   see --help. of note is --myhost, which should be set if used anywhere but localhost.
2. connect to control port
3. make sure the server did not send you a `no_available_listeners` message; if it
   did, the relay is out of ports, and you're out of luck
4. parse the listener messages
5. wait for 

When your server wants to use the relay, it must initiate a connection to the
*control port*; 12000 by default. The control protocol is a very simple line-based
protocol (delimited by \r\n). Its syntax is very simple; a command, sometimes
followed by an argument, space-separated. these are the messages defined:

- `public_listener <HOSTNAME>:<PORT>` - tells the server what its public address is;
  this is the address clients should connect to when they want to use the server.
- `reverse_listener <HOSTNAME>:<PORT>` - tells the server what its reverse address is;
  this is the address that the server should connect to to service clients.
- `new_connection` - sent when a new client comes in. server should respond by
  connecting to the address provided by `reverse_listener`; that connection becomes
  a client connection.
- `no_available_listeners` - sent by the relay when it has no more ports available
  to give to new servers. If the server receives this message, there's nothing it
  can do but wait and hope for another server to disconnect.

Again: when a new client connection comes in, your server must connect to the
reverse port; that connection becomes the session with the client. With most socket
libraries this should only be a change in initialization code.

Example session:

- `server -> relay` server connects to localhost:12000
- `server <- relay` relay sends back lines:

    public_listener localhost:12101
    reverse_listener localhost:12001

- `relay <- client` client connects to localhost:12101
- `server <- relay` relay informs server of presence of new client:

    new_connection

- `server -> relay` server connects to localhost:12001
- server uses this new connection to communicate with client

For a reference implementation and examples you can run, see `tx_tlsrelay.client`
and `bin/relayed_*server`.

Twisted Usage
-------------

Instead of `TLS4ServerEndpoint`, use `tx_tlsrelay.client.TLS4RelayServerEndpoint`
and pass it the address of the relay you wish to use. TLS4RelayServerEndpoint.listen()
returns a deferred that fires with an object that implements IListeningPort;
that object's .getHost() method returns an address object with .host and .port, which
are your server's public address.

See also:

- http://twistedmatrix.com/documents/current/core/howto/endpoints.html
- the mentions of endpoints in
  https://twistedmatrix.com/documents/current/core/howto/servers.html
- `bin/relayed_echoserver` and `bin/relayed_httpserver`
