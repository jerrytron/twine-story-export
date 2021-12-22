#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: jerrytron
# @Date:   2015-05-27 23:10:07
# @Last Modified by:   jerrytron
# @Last Modified time: 2015-05-28 16:23:31

import os
import re
import sys
import struct
import argparse
import tiddlywiki as tiddly

VERSION = "1.0"

# For holding variable keys and values.
VARIABLES = {}

TITLE_MAP = {}
STORY_MAP = {}
PASSAGES = {}
STORY_TITLE = ""
STORY_AUTHOR = ""
STORY_SUBTITLE = ""
STORY_CREDITS = ""
STORY_VERSION = ""
STORY_CONTACT = ""
STORY_LANGUAGE = ""
REPORT = ""
OPERATION_TEST = bytearray()
TOTAL_OPS = 0
VERBOSE = False

kAppend = "<append>"
kContinue = "<continue>"
kContinueCopy = 'Continue...'

class CDAMParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

def main():
    global STORY_TITLE
    global STORY_AUTHOR
    global STORY_SUBTITLE
    global STORY_CREDITS
    global STORY_CONTACT
    global STORY_LANGUAGE
    global STORY_VERSION

    # To Make a Linear Story:
    # python ./cdam_convert_twine.py --title

    parser = CDAMParser(version='1.0', description='CDAM Twine Source Code Converter')
    #parser.add_argument('--dirname', default='NONE', action='store', help='Directory name for story on the file system.')
    #parser.add_argument('--title', default='Untitled', action='store', help='The story title.')
    #parser.add_argument('--subtitle', default='NONE', action='store', help='The story subtitle.')
    #parser.add_argument('--author', default='Anonymous', action='store', help='The author of the story.')
    #parser.add_argument('--credits', default='', action='store', help='Additional story credits.')
    #parser.add_argument('--contact', default='Follow @choosatron online!', action='store', help='Misc contact info.')
    #parser.add_argument('--lang', default='eng', action='store', help='Up to four character language code.')
    #parser.add_argument('--ver', default='1.0.0', action='store', help='Story version in three parts, x.x.x')
    parser.add_argument('--source', default='', action='store', help='The Twine source code file.')
    parser.add_argument('--output', default='./', action='store', help='The location to create the output files.')

    args = parser.parse_args()

    story = LoadSource(args.source)

    if story == False:
        print("[ERROR] Failed to read file contents.")
        return

    tiddlySrc = ParsePassages(story)

    print("Done!")

def LoadSource(path):
    try:
        file = open(path, 'r')
    except IOError:
        print("[ERROR] File not found: " + path)
        return False

    #sourceStr = file.read()
    source = ""
    for line in file:
        #print line
        if line.find("Title: ") >= 0:
            # Split the line at title, grab the second part, chop off the newline.
            STORY_TITLE = line.split("Title: ", 1)[1][:-1]
            print(STORY_TITLE)
            continue
        if line.find("Subtitle: ") >= 0:
            STORY_SUBTITLE = line.split("Subtitle: ", 1)[1][:-1]
            print(STORY_SUBTITLE)
            continue
        if line.find("Author: ") >= 0:
            STORY_AUTHOR = line.split("Author: ", 1)[1][:-1]
            print(STORY_AUTHOR)
            continue
        if line.find("Credits: ") >= 0:
            STORY_CREDITS = line.split("Credits: ", 1)[1][:-1]
            print(STORY_CREDITS)
            continue
        if line.find("Contact: ") >= 0:
            STORY_CONTACT = line.split("Contact: ", 1)[1][:-1]
            print(STORY_CONTACT)
            continue
        if line.find("Language: ") >= 0:
            STORY_LANGUAGE = line.split("Language: ", 1)[1][:-1]
            print(STORY_LANGUAGE)
            continue
        if line.find("Version: ") >= 0:
            STORY_VERSION = line.split("Version: ", 1)[1][:-1]
            print(STORY_VERSION)
            continue
        source += line

    file.close()
    return source

def ParsePassages(source):
    global STORY_TITLE
    global STORY_AUTHOR
    global STORY_SUBTITLE
    global STORY_CREDITS
    global STORY_CONTACT
    global STORY_LANGUAGE
    global STORY_VERSION



def BuildTiddlyPassage():
    passage = ""

    return passage


if __name__ == '__main__':
    main()