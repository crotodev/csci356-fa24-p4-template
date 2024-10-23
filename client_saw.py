#!/usr/bin/env python3
#
# Author: K. Walsh <kwalsh@cs.holycross.edu>
# Date: 4 April 2017
# Modified: 20 October 2023
#
# Stop-and-wait client for a simple and slightly-reliable protocol on top of UDP. 
#
# What it does: This implements the stop-and-wait protocol, mostly:
#   state 0. Client waits for data to be available to send. If none, then exit.
#   state 1. Client sends one UDP packet. The server will respond with an ACK.
#   state 2. Client waits for one ACK, then go back to state 0.
# A 4-byte sequence number is included in each packet, so the server can detect
# duplicates, detect missing packets, and sort any mis-ordered packets back into
# the correct order. A 4-byte "magic" integer (0xBAADCAFE) is also included with
# each packet, for no reason at all (you can replace it with something else, or
# remove it entirely).
#
# What it doesn't do: There are no NACKs or timeouts, so if any data packet is
# lost, or any ACK packet is lost, the protocol will deadlock, simply freezing
# in step 2 forever. All ACK packets are treated identically (any numbers in
# them are completely ignored), so if data packets or ACK packets get duplicated
# in the network, things will probably go haywire.
#
# Run the program like this:
#   python3 client_saw.py 1.2.3.4 6000
# This will send data to a UDP server at IP address 1.2.3.4 port 6000.

import socket
import sys
import time
import struct
import datasource
import trace

# setting verbose = 0 turns off most printing
# setting verbose = 1 turns on a little bit of printing
# setting verbose = 2 turns on a lot of printing
# setting verbose = 3 turns on all printing
verbose = 3

tracefile = "client_saw_packets.csv"
# tracefile = None # This will disable writing a trace file for the client


def main(host, port):
    print("Sending UDP packets to %s:%d" % (host, port))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Makes a UDP socket!

    trace.init(tracefile,
            "Log of all packets sent and ACKs received by client", 
            "SeqNo", "TimeSent", "AckNo", "timeACKed")

    start = time.time()

    magic = 0xBAADCAFE # a value to be included in every data packet
    seqno = 0 # sequence number for the next data packet to be sent
    hdr = None # header for the next data packet to be sent
    body = None # data to be sent in the next data packet to be sent
    have_more_data = True # keep track of whether we have more data to send
    state = 0 # the current state for our protocol

    while have_more_data:
        if state == 0: #  wait for data to be available to send
            body = datasource.wait_for_data(seqno)
            if body == None: have_more_data = False
            else: state = 1 # go to state 1

        elif state == 1: # send one data packet
            # make a header, create a packet, and send it
            hdr = bytearray(struct.pack(">II", magic, seqno))
            pkt = hdr + body
            tSend = time.time()
            s.sendto(pkt, (host, port))

            if verbose >= 3 or (verbose >= 1 and seqno < 5 or seqno % 1000 == 0):
                print("Sent packet with seqno %d" % (seqno))

            state = 2 # go to state 2

        elif state == 2: # wait for one ACK packet, increment seqno, and print some stuff
            # wait for an ACK
            (ack, addr) = s.recvfrom(100)
            tRecv = time.time()

            # unpack integers from the ACK packet, then print some messages
            (magack, ackno) = struct.unpack(">II", ack)
            if verbose >= 3 or (verbose >= 1 and seqno < 5 or seqno % 1000 == 0):
                print("Got ack with seqno %d" % (ackno))

            # write info about the packet and the ACK to the log file
            trace.write(seqno, tSend - start, ackno, tRecv - start)

            # prepare for the next packet
            seqno += 1

            state = 0 # go back to state 0

        else:
            print(f"OOPS! Should never be in state {state}")
            break


    end = time.time()
    elapsed = end - start
    print("Finished sending all packets!")
    print("Elapsed time: %0.4f s" % (elapsed))
    trace.close()


if __name__ == "__main__":
    if len(sys.argv) <= 2:
        print("To send data to the server at 1.2.3.4 port 6000, try running:")
        print("   python3 %s 1.2.3.4 6000" % (sys.argv[0]))
        sys.exit(0)
    host = sys.argv[1]
    port = int(sys.argv[2])
    main(host, port)
