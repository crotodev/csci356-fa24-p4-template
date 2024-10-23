# Author: K. Walsh <kwalsh@cs.holycross.edu>
# Date: 4 April 2017
#
# This file writes data to a log file. The resulting file is a
# CSV (comma-separated values) format file that can be opened with a spreadsheet
# like Excel, Google Sheets, Libre/Open Office Calc, or Apple Numbers.
#
# The first line is a title.
# The second line is the title for each column.
# The rest of the lines contain the data.

csv = None
csvname = None

def init(filename, title, *args):
    global csv, csvname
    if filename is not None:
        csv = open(filename, "w")
        csv.write("#" + title + "\n")
        csv.write("#" + (",".join(args)) + "\n")
        csvname = filename
        print("**** Data will be saved to %s ****" % (csvname))

def write(*args):
    global csv
    if csv is not None:
        csv.write(",".join([str(a) for a in args]) + "\n")

def close():
    global csv, csvname
    if csv is not None:
        csv.close()
        csv = None
        print("**** Data saved to %s ****" % (csvname))
    else:
        print("**** No data saved, because tracefile = None ****")

