# IP Multicast Set of Rules.
# http://p2psp.org/en/p2psp-protocol?cap=indexsu7.xht

# {{{ Imports

from __future__ import print_function
import sys
import socket
import threading
import struct
from color import Color
import common
import time

# }}}

class Splitter_IMS(threading.Thread):
    # {{{

    # {{{ Class "constants"

    # {{{ The buffer_size (in chunks). The buffer_size should be
    # proportional to the bit-rate (remember that the latency is also
    # proportional to the buffer_size).
    # }}}
    BUFFER_SIZE = 256

    # {{{ Channel served by the streaming source.
    # }}}
    CHANNEL = "Big_Buck_Bunny_small.ogv"

    # {{{ The chunk_size (in bytes) depends mainly on the network
    # technology and should be selected as big as possible, depending
    # on the MTU and the bit-error rate.
    # }}}
    CHUNK_SIZE = 1024

    # {{{ Number of chunks of the header.
    # }}}
    HEADER_SIZE = 10

    # {{{ The unicast IP address of the splitter server.
    # }}}
    #SPLITTER_ADDR = "localhost" # No por ahora
    
    # {{{ Port used to serve the peers (listening port).
    # }}}
    PORT = 4552

    # {{{ The host where the streaming server is running.
    # }}}
    SOURCE_HOST = "localhost"

    # {{{ Port where the streaming server is listening.
    # }}}
    SOURCE_PORT = 8000

    # {{{ The multicast IP address of the team, used to send the chunks.
    # }}}
    MCAST_ADDR = "224.0.0.1" # All Systems on this subnet
    #MCAST_ADDR = "224.1.1.1"

    # }}}

    def __init__(self):
        # {{{

        threading.Thread.__init__(self)

        print("Running in", end=' ')
        if __debug__:
            print("debug mode")
        else:
            print("release mode")

        self.print_the_module_name()
        print("Buffer size (in chunks) =", self.BUFFER_SIZE)
        print("Chunk size (in bytes) =", self.CHUNK_SIZE)
        print("Channel =", self.CHANNEL)
        print("Header size (in chunks) =", self.HEADER_SIZE)
        #print("Splitter address =", self.SPLITTER_ADDR) # No ahora
        print("Listening (and multicast) port =", self.PORT)
        print("Source IP address =", self.SOURCE_HOST)
        print("Source port =", self.SOURCE_PORT)
        print("Multicast address =", self.MCAST_ADDR)

        # {{{ A IMS splitter runs 2 threads. The first one controls
        # the peer arrivals. The second one shows some information
        # about the transmission. This variable is used to stop the
        # child threads. They will be alive only while the main thread
        # is alive.
        # }}}
        self.alive = True

        # {{{ Number of the served chunk.
        # }}}
        self.chunk_number = 0

        # {{{ Used to listen to the incomming peers.
        # }}}
        self.peer_connection_socket = ""

        # {{{ Used to listen the team messages.
        # }}}
        self.team_socket = ""

        self.source_socket = ""
        
        # {{{ The video header.
        # }}}
        self.header = ""

        # {{{ Some other useful definitions.
        # }}}
        self.source = (self.SOURCE_HOST, self.SOURCE_PORT)
        self.GET_message = 'GET /' + self.CHANNEL + ' HTTP/1.1\r\n'
        self.GET_message += '\r\n'
        self.chunk_format_string = "H" + str(self.CHUNK_SIZE) + "s" # "H1024s
        self.mcast_channel = (self.MCAST_ADDR, self.PORT)

        self.recvfrom_counter = 0
        self.sendto_counter = 0
        
        # }}}

    def print_the_module_name(self):
        # {{{

        sys.stdout.write(Color.yellow)
        print("Splitter IMS")
        sys.stdout.write(Color.none)

        # }}}

    def send_the_header(self, peer_serve_socket):
        # {{{

        if __debug__:
            print("Sending a header of", len(self.header), "bytes")
        try:
            peer_serve_socket.sendall(self.header)
        except:
            pass
        
        # }}}

    def send_the_buffer_size(self, peer_serve_socket):
        # {{{

        if __debug__:
            print("Sending a buffer_size of", self.BUFFER_SIZE, "bytes")
        message = struct.pack("H", socket.htons(self.BUFFER_SIZE))
        try:
            peer_serve_socket.sendall(message)
        except:
            pass
        
        # }}}

    def send_the_chunk_size(self, peer_serve_socket):
        # {{{

        if __debug__:
            print("Sending a chunk_size of", self.CHUNK_SIZE, "bytes")
        message = struct.pack("H", socket.htons(self.CHUNK_SIZE))
        try:
            peer_serve_socket.sendall(message)
        except:
            pass
        
        # }}}

    def send_the_mcast_channel(self, peer_serve_socket):
        # {{{

        if __debug__:
            print("Communicating the multicast channel", (self.MCAST_ADDR, self.PORT))
        message = struct.pack("4sH", socket.inet_aton(self.MCAST_ADDR), socket.htons(self.PORT))
        try:
            peer_serve_socket.sendall(message)
        except:
            pass
        
        # }}}

    def send_the_header_size(self, peer_serve_socket):
        # {{{

        if __debug__:
            print("Communicating the header size", self.HEADER_SIZE)
        message = struct.pack("H", socket.htons(self.HEADER_SIZE))
        try:
            peer_serve_socket.sendall(message)
        except:
            pass
        
        # }}}

    def send_configuration(self, sock):
        self.send_the_mcast_channel(sock)
        self.send_the_header_size(sock)
        self.send_the_chunk_size(sock)
        self.send_the_header(sock)
        self.send_the_buffer_size(sock)


    def handle_a_peer_arrival(self, connection):
        # {{{ Handle the arrival of a peer. When a peer want to join a
        # team, first it must establish a TCP connection with the
        # splitter.
        
        sock = connection[0]
        peer = connection[1]
        sys.stdout.write(Color.green)
        print(sock.getsockname(), '\b: accepted connection from peer', peer)
        sys.stdout.write(Color.none)
        self.send_configuration(sock)
        sock.close()
        #self.append_peer(peer)
        return peer

        # }}}

    def handle_arrivals(self):
        # {{{ 

        while self.alive:
            peer_serve_socket, peer = self.peer_connection_socket.accept()
            threading.Thread(target=self.handle_a_peer_arrival, args=((peer_serve_socket, peer), )).start()

        # }}}

    def setup_peer_connection_socket(self):
        # {{{ Used to listen to the incomming peers.

        self.peer_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # This does not work in Windows systems.
            self.peer_connection_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except: # Falta averiguar excepcion
            pass

        try:
            #self.peer_connection_socket.bind((socket.gethostname(), self.PORT))
            self.peer_connection_socket.bind(('', self.PORT))
        except: # Falta averiguar excepcion
            raise

        # {{{ Set the connection queue to the max!
        # }}}
        self.peer_connection_socket.listen(socket.SOMAXCONN) 

        # }}}

    def setup_team_socket(self):
        # {{{ Used to talk with the peers of the team. In this case,
        # it corresponds to a multicast channel.
        
        #self.team_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.team_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        
        self.team_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        try:
            # This does not work in Windows systems !!
            self.team_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            pass
        try:
            #self.team_socket.bind((socket.gethostname(), self.PORT))
            self.team_socket.bind(('', self.PORT))
        except:
            raise

        # }}}

    def request_the_video_from_the_source(self):
        # {{{ Request the video using HTTP from the source node (Icecast).

        self.source_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if __debug__:
            print(self.source_socket.getsockname(), 'connecting to the source', self.source, '...')
        self.source_socket.connect(self.source)
        if __debug__:
            print(self.source_socket.getsockname(), 'connected to', self.source)
        self.source_socket.sendall(self.GET_message)
        if __debug__:
            print(self.source_socket.getsockname(), 'GET_message =', self.GET_message)
        #return source_socket

        # }}}

    def receive_next_chunk(self, header_load_counter):
        # {{{

        #print(self.source_socket.getpeername())
        chunk = self.source_socket.recv(self.CHUNK_SIZE)
        prev_size = 0
        while len(chunk) < self.CHUNK_SIZE:
            if len(chunk) == prev_size:
                # This section of code is reached when the streaming
                # server (Icecast) finishes a stream and starts with
                # the following one.
                print('?', end='')
                sys.stdout.flush()
                self.source_socket.close()
                time.sleep(1)
                self.source_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.source_socket.connect(self.source)
                #print(self.source_socket.getpeername())
                self.source_socket.sendall(self.GET_message)
                self.header = ""
                header_load_counter = self.HEADER_SIZE
                chunk = ""
            prev_size = len(chunk)
            chunk += self.source_socket.recv(self.CHUNK_SIZE - len(chunk))
        return chunk, header_load_counter

        # }}}

    def configure_sockets(self):
        # {{{ setup_peer_connection_socket()

        try:
            self.setup_peer_connection_socket()
        except Exception, e:
            print(e)
            print(self.peer_connection_socket.getsockname(), "\b: unable to bind the port ", self.PORT)
            sys.exit('')

        # }}}

        # {{{ setup_team_socket()

        try:
            self.setup_team_socket()
        except Exception, e:
            print(e)
            print(self.team_socket.getsockname(), "\b: unable to bind", (socket.gethostname(), self.PORT))
            sys.exit('')

        # }}}

    def load_the_video_header(self):
        # {{{ Load the video header.

        for i in xrange(self.HEADER_SIZE):
            self.header += self.receive_next_chunk(0)[0]

        # }}}

    def receive_chunk(self, header_load_counter):
        # {{{

        chunk, header_load_counter = self.receive_next_chunk(header_load_counter)

        if header_load_counter > 0:
            print("Loaded", len(self.header), "bytes of header")
            self.header += chunk
            header_load_counter -= 1

        self.recvfrom_counter += 1
            
        return chunk

        # }}}

    def send_chunk(self, chunk, endpoint):
        # {{{

        message = struct.pack(self.chunk_format_string, socket.htons(self.chunk_number), chunk)
        self.team_socket.sendto(message, endpoint)

        if __debug__:
            print('%5d' % self.chunk_number, Color.red, '->', Color.none, endpoint)
            sys.stdout.flush()

        self.sendto_counter += 1
        
        # }}}

    def receive_and_send_a_chunk(self, header_load_counter): # Sin usar
        # {{{

        # Receive data from the source
        chunk, header_load_counter = self.receive_next_chunk(header_load_counter)

        if header_load_counter > 0:
            print("Header load counter =", header_load_counter)
            self.header += chunk
            header_load_counter -= 1

        message = struct.pack(self.chunk_format_string, socket.htons(self.chunk_number), chunk)
        self.team_socket.sendto(message, self.mcast_channel)

        if __debug__:
            print('%5d' % self.chunk_number, Color.red, '->', Color.none, self.mcast_channel)
            sys.stdout.flush()

        # }}}

    def receive_the_header(self):
        self.configure_sockets()
        self.request_the_video_from_the_source()
        self.load_the_video_header()

    def run(self):
        # {{{

        self.receive_the_header()
        
        print(self.peer_connection_socket.getsockname(), "\b: waiting for a peer ...")
        self.handle_a_peer_arrival(self.peer_connection_socket.accept())
        threading.Thread(target=self.handle_arrivals).start()

        header_load_counter = 0
        while self.alive:
            #self.receive_and_send_a_chunk(header_load_counter)
            self.send_chunk(self.receive_chunk(header_load_counter), self.mcast_channel)
            self.chunk_number = (self.chunk_number + 1) % common.MAX_CHUNK_NUMBER

        # }}}

    # }}}

