#!/usr/bin/env python3
#
# Author: K. Walsh <kwalsh@cs.holycross.edu>
# Date: 4 April 2017
# Modified: 20 October 2023
#
# Burst-oriented client for a simple and semi-reliable protocol on top of UDP. 
#
# What it does: This version blasts UDP packets in bursts at the server, with N
# packets in each burst, each burst sent as fast as possible, and a T second
# delay between the end of one burst and the beginning of the next.
#   state 0. Client waits for data to be available to send. If the seqno is a
#           multiple of N, this is the start of a burst, so go to state 1, else
#           go to state 2.
#   state 1. Wait T seconds, to leave a gap between bursts.
#   state 2. Sends one UDP packet. Don't wait for ack, just go back to state 0.
# A 4-byte sequence number is included in each packet, so the server can detect
# duplicates, detect missing packets, and sort any mis-ordered packets back into
# the correct order. A 4-byte "magic" integer (0xBAADF00D) is also included with
# each packet, for no reason at all (you can replace it with something else, or
# remove it entirely).
#
# What it doesn't do: There is no congestion or flow control of any kind, except
# for the delay between bursts, no ACKs or NACKs, no retransmission upon loss,
# no timeouts, and no other fancy features.
#
# Run the program like this:
#   python3 client_burst1.py 1.2.3.4 6000 50 0.120
# This will send data to a server at IP address 1.2.3.4 port 6000, with N=50
# packets per burst, and T=0.120 seconds (or 120 ms) between the end of one
# burst and the beginning of the next.

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
verbose = 0

tracefile = "client_burst1_packets.csv"
# tracefile = None # This will disable writing a trace file for the client


def main(host, port, n, t):
    print("Sending UDP packets to %s:%d with burst size N=%d and T=%f s between bursts" % (host, port, n, t))
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
    burst = -1 # current burst number
    state = 0 # the current state for our protocol

    while have_more_data:
        if state == 0: #  wait for data to be available to send
            body = datasource.wait_for_data(seqno)
            if body == None: have_more_data = False
            elif seqno % n == 0: state = 1 # go to state 1
            else: state = 2 # go to state 2
        
        elif state == 1: # wait T seconds for the gap between bursts
            time.sleep(t)
            state = 2

        elif state == 2: # send one data packet
            # make a header, create a packet, and send it
            hdr = bytearray(struct.pack(">II", magic, seqno))
            pkt = hdr + body
            tSend = time.time()
            s.sendto(pkt, (host, port))

            # print stuff
            if verbose >= 3 or (verbose >= 1 and seqno < 5 or seqno % 1000 == 0):
                print("Sent packet with seqno %d" % (seqno))

            # write info about the packet (but without the ACK) to the log file
            trace.write(seqno, tSend - start, 0, 0)

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
    if len(sys.argv) <= 4:
        print("To send data to server 1.2.3.4 port 6000, try running:")
        print("   python client_burst1.py 1.2.3.4 6000 50 0.120")
        sys.exit(0)
    host = sys.argv[1]
    port = int(sys.argv[2])
    n = int(sys.argv[3])
    t = float(sys.argv[4])
    main(host, port, n, t)
