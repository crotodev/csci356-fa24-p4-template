# Author: K. Walsh <kwalsh@cs.holycross.edu>
# Date: 4 April 2017
# Modified: 20 October 2023
#
# A source of example payload data for testing TCP-like semi-reliable protocols.
#
# The data is not random, instead it's taken from various images and videos. The
# images and video are all 480 x 360 pixels, 3 bytes per pixel. To keep things
# simple, each data packet is one row of an image, so each packet will contain:
#    480 pixels x 3 bytes per pixel = 1440 bytes
#
# We use 3 different images, followed by a video with 496 frames, followed
# by one more image, so in all we have:
#    500 images * 360 packets per image = 180,000 packets
#    180,000 packets * 1440 bytes per packet = about 260 MB

from PIL import Image
import imageio
import signal
import sys
import trace

width = 480
height = 360
numFrames = 500

numPackets = numFrames * height # 180000

# This function returns example payload data for a given sequence number.
def wait_for_data(seqno, quiet=False):
    if seqno < 0:
        raise Exception("Oops, seqno %s is negative!" % (str(seqno)))
    if seqno >= numPackets:
        return None
    f = seqno // height;
    y = seqno % height;
    if f == 0:
        return get_image_packet(img3, y)
    elif f == 1:
        return get_image_packet(img2, y)
    elif f == 2:
        return get_image_packet(img1, y)
    elif f < numFrames-1:
        return get_video_packet(vid, f, y)
    else:
        return get_image_packet(img0, y)

# If the program is ever killed using Control-C, save the trace before quitting.
def signal_handler(signal, frame):
    print("Exiting...")
    trace.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


# The remainder of this file is used to generate the example data.

def load_image(filename):
    im = Image.open(filename)
    return im.load()

def get_image_packet(img, y):
    row = [img[x,y] for x in range(width)]
    return bytearray(sum(row, ()))

def load_video(filename):
    vid = imageio.get_reader(filename,  'ffmpeg')
    frames = []
    for i, img in enumerate(vid):
        if i < 20:
            continue
        if i > 20+numFrames:
            break
        frames.append(img.tostring())
    return frames

def get_video_packet(vid, f, y):
    # print(f)
    data = vid[f]
    return bytearray(data[y*width*3:(y+1)*width*3])

print("Loading example data...")
img3 = load_image("/var/streaming/colorbars3.png")
img2 = load_image("/var/streaming/colorbars2.png")
img1 = load_image("/var/streaming/colorbars1.png")
vid = load_video("/var/streaming/video.mp4")
img0 = load_image("/var/streaming/done.png")
# the next few lines ensure the data is ready to go
get_image_packet(img3, 0)
get_image_packet(img2, 0)
get_image_packet(img1, 0)
get_video_packet(vid, 0, 0)
get_image_packet(img0, 0)
print("... example data is ready.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("There are %d packets of data to be sent, taken from %d images." % (numPackets, numFrames))
        print("You can see info about packets. For example, to see info about packet 0, run:")
        print("   python datasource.py 0")
    if len(sys.argv) == 2 and sys.argv[1] == "dump":
        print("Dumping %d packets x 1440 = %d bytes to file: streaming.bin" % (numPackets, numPackets * 1440))
        with open("streaming.bin", "bw") as outfile:
            for seqno in range(numPackets):
                pkt = wait_for_data(seqno)
                outfile.write(pkt)
        print("Done.")
        sys.exit(0)
    for seqno in [int(arg) for arg in sys.argv[1:]]:
        pkt = wait_for_data(seqno, True)
        print("Packet with seqno=%d contains %d bytes" % (seqno, len(pkt)))
        print("(This is RGB image data for frame %d, row %d)" % (seqno / height, seqno % height))
        print("Packet data (in hex) is:")
        i = 0
        for b in pkt:
            print("%02x " % (b), end = '')
            i = i+1
            if i >= 32:
                print()
                i = 0

