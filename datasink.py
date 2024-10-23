# Author: K. Walsh <kwalsh@cs.holycross.edu>
# Date: 4 April 2017
#
# This file consumes packets as they are received by a server. It also
# calculates and prints some statistics.

import time
import os
import signal
import sys
import struct
import threading
from queue import Queue
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import http.server
import socketserver
import trace
import datasource

# setting verbose = 0 turns off most printing
# setting verbose = 1 turns on a little bit of printing
# setting verbose = 2 turns on a lot of printing
# setting verbose = 3 turns on all printing
verbose = 2

# setting shortStats = True makes the printing a little more condensed
shortStats = True

# statistics
startTime = None
endTime = None
totalBytes = 0
totalPackets = 0
uniquePackets = 0
duplicatePackets = 0
misorderedPackets = 0
expectedSeqno = 0
highestSeqno = -1

# deliver() uses the seqno to put payloads into the proper order, and marks that
# seqno as having been received. It also prints various statistics. It returns a
# number indicating how many times this seqno has been seen. So it will return 1
# the first time a seqno is seen, and it will return larger numbers when a seqno
# is a duplicate of some previous packet.
def deliver(seqno, payload):
    # Keep track of the most recent packet arrival time
    global startTime, endTime, totalPackets
    endTime = time.time_ns()
    if totalPackets == 0:
        startTime = endTime

    # Put the packet into a queue to be sent to the browser, if there is one.
    if recentPackets is not None:
        recentPackets.put((endTime - startTime, seqno, payload))

    # Mark the packet as having been received.
    n = mark_as_received(seqno)

    # Update statistics and print warning/error messages.
    global highestSeqno, expectedSeqno, totalBytes, uniquePackets, duplicatePackets, misorderedPackets
    totalBytes = totalBytes + len(payload)
    totalPackets = totalPackets + 1
    if n > 1:
        duplicatePackets = duplicatePackets + 1
        if duplicatePackets <= 10 or verbose >= 2 :
            print("Oops, got seqno %d, but already got that %d times" % (seqno, n-1))
            if duplicatePackets == 10 and verbose < 2:
                print("  (supressing further messages like this)")
    else:
        uniquePackets = uniquePackets + 1
        if not seqno == expectedSeqno:
            misorderedPackets = misorderedPackets + 1
            if misorderedPackets <= 10 or verbose >= 2:
                print("Oops, got seqno %d, but was expecting seqno %d" % (seqno, expectedSeqno))
                if misorderedPackets == 10 and verbose < 2:
                    print("  (supressing further messages like this)")
    expectedSeqno = seqno + 1
    highestSeqno = max(highestSeqno, seqno)

    # Print statistics, but not for every packet.
    if totalPackets == 1:
        if verbose >= 2:
            print("First packet arrived: seqno = %d, payload length = %d bytes" % (seqno, len(payload)))
    else:
        if verbose >= 3:
            print("A new packet arrived: seqno = %d, payload length = %d bytes" % (seqno, len(payload)))
        if verbose >= 2 and (
                (totalPackets < 10) or
                (totalPackets < 100 and totalPackets % 10 == 0) or
                (totalPackets < 1000 and totalPackets % 100 == 0) or
                (totalPackets < 10000 and totalPackets % 1000 == 0)):
            showStats()
        elif totalPackets % 10000 == 0:
            showStats()

    # Return a count of how many times this packet has been seen so far.
    return n


# The rest of this file is for printing statistics, sending data to a web
# browser, keeping track of which packets have been received, etc.

def kb(n):
    if n < 1024:
        return "%d B" % (n)
    elif n < 1024*1024:
        return "%0.2f KB" % (n/1024.0)
    elif n < 1024*1024*1024:
        return "%0.2f MB" % (n/1024.0/1024.0)
    else:
        return "%0.2f GB" % (n/1024.0/1024.0/1024.0)

def showStats():
    global startTime, highestSeqno, expectedSeqno, totalBytes, totalPackets, uniquePackets, duplicatePackets, misorderedPackets

    totalTime = (endTime - startTime) / 1000000000
    bytesPerSecond = totalBytes / totalTime
    missingPackets = highestSeqno+1 - uniquePackets
    if shortStats:
        print("elapsed time %0.3f s, total received %s, throughput %s" %
                (totalTime, kb(totalBytes), kb(bytesPerSecond)+"ps"))
        print("  %d packets, %d unique, %d duplicate, %d misordered, %d missing" %
                (totalPackets, uniquePackets, duplicatePackets,
                misorderedPackets, missingPackets))
    else:
        print("  Elapsed time: %0.3f s" % (totalTime))
        print("  Total Packets: %d" % (totalPackets))
        print("  Unique Packets: %d" % (uniquePackets))
        print("  Missing packets: %d" % (missingPackets))
        print("  Duplicate packets: %d" % (duplicatePackets))
        print("  Out-of-order packets: %d" % (misorderedPackets))
        print("  Data: %s" % (kb(totalBytes)))
        print("  Throughput: %s" % (kb(bytesPerSecond)+"ps"))


# A list tracking how many times each seqno has been received.
# Anything over 180,000 is ignored.
seqno_count = [0] * 180000

def mark_as_received(seqno):
    global seqno_count
    if seqno < 0 or seqno >= 180000:
        return 1
    n = seqno_count[seqno] = seqno_count[seqno] + 1
    return n

def count_times_received(seqno):
    global seqno_count
    if seqno < 0 or seqno >= 180000:
        return
    return seqno_count[seqno]
    return n

# A queue of recent (seqno, packet) data, to be sent to browser for display.
recentPackets = None

class HTTPHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/var/streaming", **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.do_GET_Index()
        else:
            http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_GET_Index(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-length", len(HTTPHandler.index))
        self.end_headers()
        self.wfile.write(HTTPHandler.index)

    # def end_headers(self):
    #     # Everything we serve is cacheable, it never changes
    #     self.send_header('Cache-Control', 'public, max-age=604800')  # 1 week = 7 * 24 * 3600
    #     self.send_header('Pragma', 'cache')  # Optional older HTTP/1.0 header
    #     super().end_headers()  # Call the default handler to complete the process

def handle_websocket_connection(ws):
    global recentPackets
    recentPackets = Queue()
    ws.sendMessage("welcome")
    while True:
        (arrivalTime, seqno, payload) = recentPackets.get(True)
        hdr = bytearray(struct.pack(">QI", arrivalTime, seqno))
        try:
            body = datasource.wait_for_data(seqno, True)
            if body == payload:
                payload = b"" # do not send payload to browser if it matches seqno
        except:
            pass
        # print(f"sending {len(hdr)} + {len(payload)} bytes to websocket")
        ws.sendMessage(hdr + payload)
        # recentPackets.task_done()

class WSHandler(WebSocket):

    def handleMessage(self):
        print("Unexpected message from browser", self.address)

    def handleConnected(self):
        print("Connection from browser", self.address)
        t = threading.Thread(target=handle_websocket_connection, args=(self,))
        t.daemon = True
        t.start()

    def handleClose(self):
        print("Disconnection from browser", self.address)

httpd = None
wsd = None
httpHost = None
httpPort = None
wsHost = None
wsPort = None
wsUser = None

def init(host):
    global httpd, wsd, httpHost, httpPort, wsHost, wsPort, wsUser, recentPackets

    wsUser = os.getenv("USER", "unknown user")

    # find a port and start the web-socket server
    for port in range(8100, 8180):
        try:
            wsd = SimpleWebSocketServer("", port, WSHandler)
            wsHost = host
            wsPort = port
            break
        except:
            pass
    if wsd is None:
        print("************************************************************")
        print("Warning: Could not find a suitable port around 8100 for")
        print("         web-socket server. Web view will not be available.")
        print("************************************************************")
        return

    for port in range(8000, 8080):
        try:
            socketserver.TCPServer.allow_reuse_address = True
            httpd = socketserver.TCPServer(("", port), HTTPHandler)
            httpHost = host
            httpPort = port
            break
        except Exception as e:
            print("Exception", e)
            pass
    if httpd is None:
        print("**********************************************************")
        print("Warning: Could not find a suitable port around 8000 for")
        print("         HTTP server. Web view will not be available.")
        print("**********************************************************")
        return

    with open('/var/streaming/index.html', 'r') as f:
        s = f.read()
        s = s.replace('{{WSURL}}', 'ws://%s:%d/' % (wsHost, wsPort))
        s = s.replace('{{WSUSER}}', wsUser)
        HTTPHandler.index = s.encode()

    t = threading.Thread(target=wsd.serveforever, args=())
    t.daemon = True
    t.start()
    time.sleep(0.1)

    t = threading.Thread(target=httpd.serve_forever, args=())
    t.daemon = True
    t.start()
    time.sleep(0.1)

    print("Web-socket server listening at ws://%s:%d/" % (wsHost, wsPort))
    print("HTTP server listening at http://%s:%d/" % (httpHost, httpPort))
    print("To see statistics and image data, visit:")
    print("       http://%s:%d/" % (httpHost, httpPort))

    def signal_handler(signal, frame):
        print("Exiting...")
        if totalPackets > 1:
            showStats()
        trace.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
