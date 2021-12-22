#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import argparse
import struct
import time
import string
import calendar
import datetime
import pytz
from datetime import timedelta, tzinfo
import array
import shutil
import string
import uuid
import hashlib
import bitarray
#import regex as re
#import unicodedata
#from unidecode import unidecode

# cc = Can Continue <Boolean>
# cs = Choice Set <Array of Strings>
# en = Ending <Boolean>
# eq = Ending Quality <Byte, range 1-5>
# pt = Passage Text <String>
# pp = Passage Points <Byte, range 0-255>
# lc = LED Color ????
# sn = Sound Definition
# pv = Passage Version
VERSION = "1.0"

# For generating the story header binary.
LANG_MAX = 4
TITLE_MAX = 64
SUBTITLE_MAX = 32
AUTHOR_MAX = 48
CREDITS_MAX = 80
CONTACT_MAX = 128
# How many bytes per character.
CHAR_BYTE_SIZE = 1
# Number of bytes word substitution (sub byte + bytes for offset address)
OFFSET_ADDR_SIZE = 3
# Minimum length word to replace with offset.
WORD_LEN_MIN = 4
# Number of bytes to use for passage length.
PSG_LENGTH_BYTES = 4
# Number of bytes for the offset of passages.
PSG_OFFSET_BYTES = 4

# Unique 'words' by index
WORD_MAP = {}
# Frequency of mapped words.
WORD_FREQUENCY = {}
# 'words' are key to get index value
WORD_ORDER = []

PASSAGE_KEYS =  ['cc', 'cs', 'en', 'eq', 'pt', 'pp', 'pv']
PASSAGE_TYPES = ['bool', 'array', 'bool', 'int', 'string', 'int']
PASSAGE = {'cc': False, 'cs':[], 'en':False, 'eq':0, 'pp':0, 'pt':'', 'pv':'1.0'}

MAX_STORIES = 4

#PUNCTUATION = { 0x2018:0x27, 0x2019:0x27, 0x201C:0x22, 0x201D:0x22 }
#PUNCTUATION = { u'\u2018':"'", u'\u2019':"'", u'\u201C':'"', u'\u201D':'"' }

class FixedOffset(tzinfo):
    """Fixed offset in minutes: `time = utc_time + utc_offset`."""
    def __init__(self, offset):
        self.__offset = timedelta(minutes=offset)
        hours, minutes = divmod(offset, 60)
        #NOTE: the last part is to remind about deprecated POSIX GMT+h timezones
        #  that have the opposite sign in the name;
        #  the corresponding numeric value is not used e.g., no minutes
        self.__name = '<%+03d%02d>%+d' % (hours, minutes, -hours)
    def utcoffset(self, dt=None):
        return self.__offset
    def tzname(self, dt=None):
        return self.__name
    def dst(self, dt=None):
        return timedelta(0)
    def __repr__(self):
        return 'FixedOffset(%d)' % (self.utcoffset().total_seconds() / 60)

class CDAMParser(argparse.ArgumentParser):
   def error(self, message):
      sys.stderr.write('error: %s\n' % message)
      self.print_help()
      sys.exit(2)

def main():
   parser = CDAMParser(version='1.0', description='CDAM File Structure Generator')
   parser.add_argument('--map', default='', action='store', help='The file with the JSON structure mapping the story.')
   parser.add_argument('--output', default='./', action='store', help='The location to create the output files.')
   parser.add_argument('--update', action='store_true', help='Attempt to safely add to/update existing files without damaging existing data.')
   parser.add_argument('--force', action='store_true', help='Overwrite files that already exist.')
   args = parser.parse_args()

   if args.update and args.force:
      print("Conflicting flags set. Remove either update or force flag.")
      return

   gen = CDAMGenFiles()

   jsonMap = gen.LoadMapJson(args.map)
   if jsonMap == False:
      print("Exiting...")
      return

   # If you want the full path...
   path = os.path.split(args.map)[0]
   for key in jsonMap:
      filepath = os.path.join(path, key.upper())
      gen.CreatePassageFile(jsonMap[key], filepath, args.update, args.force)

class CDAMGenFiles:

   def LoadMapJson(self, path):
      try:
         file = open(path, 'r')
      except IOError:
         print("[ERROR] File not found: " + path)
         return False

      jsonStr = file.read()
      file.close()
      return json.loads(jsonStr)

   def BuildCDAMStory(self, dirname, nodeMap, passages, path, title, author, json=False):

      if json == True:
         storyDir = path
         mapPath = os.path.join(path, title + ".TXT")
         print("Creating story map file...")
         result = self.CreateMapFile(nodeMap, mapPath)
         if result == False:
            return False
      else:
         storyDir = os.path.join(path, dirname.upper())
         if not os.path.exists(storyDir):
            try:
               os.makedirs(storyDir)
            except OSError:
               if os.path.exists(storyDir):
                  pass
               else:
                  raise
         #else:
         #	shutil.rmtree(storyDir)
         #	os.makedirs(storyDir)
         # Write the title of the story in it's directory.
         titlePath = os.path.join(storyDir, "T")
         self.WriteToFile(titlePath, self.WrapString(title, 30))

         # Write the author of the story in it's directory.
         authorPath = os.path.join(storyDir, "A")
         self.WriteToFile(authorPath, author)

      print("Creating passage files...")
      for key in passages:
         filepath = os.path.join(storyDir, key.upper())
         result = self.CreatePassageFile(key, filepath, False, True, nodeMap, passages[key], json)
         if result == False:
            return False

      print("Complete")
      return True

   def UpdateManifest(self, path, title, dirname, author, json=False):
      dirname = dirname.upper()
      storyListPath = os.path.join(path, "_/T")
      needManifest = False
      total = 0
      storyId = 0

      try:
         os.makedirs(os.path.join(path, "_"))
      except OSError as e:
         if not os.path.exists(os.path.join(path, "_")):
            return False
      try:
         file = open(storyListPath, 'r')
      except IOError:
         needManifest = True
         storyId = 1
         total = 1
         print("Manifest files not defined, generating...")

      if needManifest:
         print("Creating story manifest...")
         if dirname != "NONE":
            print("[WARNING] Can't update story number when no manifest exists.")
         storyTitle = str(storyId) + "." + title
         storyTitle = self.WrapString(storyTitle, 32)
         self.WriteToFile(storyListPath, storyTitle + "\n")
      else:
         print("Updating story manifest...")
         found = False
         nextStory = False
         storyList = ""
         total = 0
         for line in file:
            if line == "\n":
               continue
            if not found:
               if line[0] == dirname:
                  if line[1] == '.':
                     print("Updating story number " + dirname)
                     storyTitle = dirname + "." + title
                     #storyTitle = self.WrapString(storyTitle, 32)
                     storyList += storyTitle + "\n"
                     storyId = int(line.split('.', 1)[0]);
                     found = True
               else:
                  storyList += line
            else:
               if line[1] == '.':
                  nextStory = True
               if not nextStory:
                  continue
               else:
                  storyList += line
            total += 1
            #if re.search('^\d\.', line):
               #total = int(line.split('.', 1)[0]);
         file.close();
         if not found:
            if dirname != "NONE":
               print("[WARNING] Unable to find story number " + dirname + " to update. Adding new story.")
            total += 1
            storyId = total
            storyTitle = str(storyId) + "." + title
            #storyTitle = self.WrapString(storyTitle, 32)
            storyList += storyTitle + "\n"
         self.WriteToFile(storyListPath, storyList)

      storyTotalPath = os.path.join(path, "_/C")
      self.WriteToFile(storyTotalPath, bytearray([total]))

      storyMaxPath = os.path.join(path, "_/M")
      self.WriteToFile(storyMaxPath, bytearray([MAX_STORIES]))
      return str(storyId)

   def GenerateBody(self, nodeMap, passages, variables):
      print("Generating Story Body...")
      body = bytearray()

      binPassages = {}
      binOrder = []

      # Number of 8 bit integer variables in story.
      #small = len(smallVars)
      #body += bytes(small)

      # Setup variable default values.
      #for smallVar in smallVars:
         #print "Small Var: " + smallVar + ", Default Value: " + str(smallVars[smallVar]['default'])
      #	body += bytes(int(smallVars[smallVar]['default']))

      # Number of 16 bit integer variables in story.
      #big = len(bigVars)
      #body += bytes(big)

      #for bigVar in bigVars:
         #print "Big Var: " + bigVar + ", Default Value: " + str(bigVars[bigVar]['default'])
      #	body += bytearray(struct.pack('<H', int(bigVars[bigVar]['default'])))

      # Generate the passage binary data.
      for index in range(0, len(passages)):
         key = str(index)
         p = passages[key]
         psgInfo = self.GeneratePassage(nodeMap, p, key, variables)
         binPassages[key] = psgInfo
         binOrder.append(key)

      # Add number of passages - 2 bytes
      body += bytearray(struct.pack('<H', len(binPassages)))
      print("# passages: " + str(len(binPassages)))
      print("body: " + str(len(body)))

      # Track the previous offset to add passage length to.
      lastOffset = 0
      for index in range(0, len(binPassages)):
         binPsg = binPassages[binOrder[index]]

         # Compress the passage.
         binPsg['compressed'] = self.CompressPassage(binPsg['bin'])

         # Add to the table of contents, which is byte offset of each passage.
         body += bytearray(struct.pack('<L', lastOffset))
         lastOffset = (lastOffset + len(binPsg['compressed']) + 1)
         #print "Passage " + str(index) + " offset: " + str(lastOffset)

         # Below this is just DEBUG
         # If it is an ending, skip.
         if binPsg['offsets'] == "end":
            continue

         # Unpack as little endian 2 byte short, returns a tuple.
         #for offset in binPsg['offsets']:
            #offsetIndex = struct.unpack_from('<H', binPsg['bin'], offset)[0]
            #print "Offset Index: " + str(offsetIndex)

      for index in range(0, len(binPassages)):
         binPsg = binPassages[binOrder[index]]

         # Add passage length bytes.
         #body += bytearray(struct.pack('<L', len(binPsg['compressed'])))
         # Add passage data.
         body += bytearray(binPsg['compressed'])
         # End of passage byte.
         body += bytes.fromhex('03')

      #self.BuildDictionary(nodeMap, passages)
      return body

   def CompressPassage(self, passageBytes):
      # TODO: This is where we might do something like a Huffman Encoding
      # The current design should work as such where compression can be
      # plugged in here without disrupting anything. The length of the
      # passage will be the bytes immediately prior, and unencoded.
      return passageBytes

   def GeneratePassage(self, nodeMap, passage, key, variables):
      info = {}
      data = bytearray()

      # Get the list of value updates.
      valueUpdates = passage['vu']
      # Set the 'append' flag.
      psgAttribute = ""
      append = False
      pressToContinue = False

      if 'cs' in passage and len(passage['cs']) == 1 and passage['cs'][0]['text'] == "*":
         print("Passage Append: " + key)
         psgAttribute += "1"
         append = True
      else:
         psgAttribute += "0"

      if 'cs' in passage and len(passage['cs']) == 1 and passage['cs'][0]['text'] == '<continue>':
         print("Passage Continue: " + key)
         psgAttribute += "1"
         pressToContinue = True
      else:
         psgAttribute += "0"

      # Add attribute padding.
      psgAttribute += "000000"
      data += bitarray.bitarray(psgAttribute)
      #data += int(psgAttribute).to_bytes(2, byteorder='big')

      # Add # of value updates for passage - 1 byte
      data += len(valueUpdates).to_bytes(1, byteorder='big')
      for update in valueUpdates:
         data += update
         #types = ""
         #valOne = 0
         #valTwo = 0

         # Variable type - still needed? Only one type of variable, and it can only BE a variable.
         #types += "11"
         #valOne = variables[update["valueOne"]]["index"]

         #if update["valueTwoType"] == "raw":
         #	types += "00"
         #	valTwo = int(update["valueTwo"])
         #elif update["valueTwoType"] == "var":
         #	types += "11"
         #	valTwo = variables[update["valueTwo"]]["index"]

         #if update["operation"] == "=":
         #	types += "0000"
         #elif update["operation"] == "+":
         #	types += "0001"
         #elif update["operation"] == "-":
         #	types += "0010"
         #elif update["operation"] == "*":
         #	types += "0011"
         #elif update["operation"] == "/":
         #	types += "0100"
         #elif update["operation"] == "%":
         #	types += "0101"
         #data += bytes(int(types, 2))

         # Add Value One
         #data += bytearray(struct.pack('<H', int(valOne)))

         # Add Value Two
         #data += bytearray(struct.pack('<H', int(valTwo)))

      # Add text body length - 2 bytes
      data += bytearray(struct.pack('<H', len(passage['pt'])))
      data += bytearray(self.translate_unicode(passage['pt']))

      attribute = ""

      if passage['en'] == True:
         # This is an ending

         # Set Choice Count byte to 0
         data += bytes.fromhex('00')

         if passage['eq'] == 1:
            attribute += "0000001"
         elif passage['eq'] == 2:
            attribute += "0000010"
         elif passage['eq'] == 3:
            attribute += "0000011"
         elif passage['eq'] == 4:
            attribute += "0000100"
         elif passage['eq'] == 5:
            attribute += "0000101"
         elif passage['eq'] == 0:
            attribute += "0000000"
         info['offsets'] = 'end'
         #data += bytes(int(attribute, 2))
         data += bitarray.bitarray(attribute)
      else:
         #print passage
         # Add # of choices - 1 byte
         choices = passage["cs"]
         data += len(choices).to_bytes(1, byteorder='big')

         #append = False
         info['offsets'] = []

         # Set the 'append' flag.
         #if len(passage['cs']) == 1 and passage['cs'][0] == "*":
         #	attribute += "1"
         #	append = True
         #else:
         #	attribute += "0"
         # Add attribute padding.
         attribute += "00000000"

         index = 0
         for choice in choices:
            try:
               # Add the attribute byte - needed every choice.
               data += bitarray.bitarray(attribute)

               conditions = passage["cdc"][index]

               # print "Condition Count: " + str(len(conditions))

               # Number of conditions
               data += len(conditions).to_bytes(1, byteorder='big')

               for condition in conditions:
                  data += condition

                  #types = ""
                  #valOne = 0
                  #valTwo = 0

                  # Variable type - still needed? Only one type of variable, and it can only BE a variable.
                  #types += "11"
                  #valOne = variables[condition["valueOne"]]["index"]

                  #if condition["valueTwoType"] == "raw":
                  #	types += "00"
                  #	valTwo = int(condition["valueTwo"])
                  #elif condition["valueTwoType"] == "var":
                  #	types += "11"
                  #	valTwo = variables[condition["valueTwo"]]["index"]

                  #if condition["operation"] == "=" or condition["operation"] == "==":
                  #	types += "0000"
                  #elif condition["operation"] == ">":
                  #	types += "0001"
                  #elif condition["operation"] == "<":
                  #	types += "0010"
                  #elif condition["operation"] == ">=":
                  #	types += "0011"
                  #elif condition["operation"] == "<=":
                  #	types += "0100"
                  #elif condition["operation"] == "%":
                  #	types += "0101"
                  #data += bytes(int(types, 2))

                  # Add Value One
                  #data += bytearray(struct.pack('<H', valOne))

                  # Add Value Two
                  #data += bytearray(struct.pack('<H', valTwo))
            except:
               # No conditions.
               #print "No Conditions"
               data += bytes.fromhex('00')

            try:
               length = passage["cvu"][index]["totalBytes"]
               #print "Length: " + str(length)
               data += bytearray(struct.pack('<H', length))

               updates = passage["cvu"][index]["data"]
               # print "Update Count: " + str(len(updates))
               data += len(updates).to_bytes(1, byteorder='big')

               if updates != 0:
               # Number of updates
                  for update in updates:
                     data += update
               else:
                  data += bytes.fromhex('00')
            except:
               # No value updates.
               data += bytes.fromhex('00') # Add two bytes for update length
               data += bytes.fromhex('00') # ""
               data += bytes.fromhex('00') # Add one byte for update count

            # Choice text length.
            if append:
               data += bytes.fromhex('00')
            elif pressToContinue:
               data += bytes.fromhex('00')
            else:
               #print "Single Choice Text Length: " + str(len(choice))
               data += bytearray(struct.pack('<H', len(choice["text"])))

            # Choice text.
            if append:
               data += bytes.fromhex('00')
            elif pressToContinue:
               data += bytes.fromhex('00')
            else:
               data += bytearray(self.translate_unicode(choice["text"]))

            # Passage offset.
            offset = int(nodeMap[key][index])
            #print "key: " + key
            #print nodeMap[key]
            #print "Choice Index: " + str(index)
            info['offsets'].append(len(data))
            #print "Offset index: " + str(offset)
            data += bytearray(struct.pack('<H', offset))

            index += 1
      info['bin'] = data
      return info


   def ReplaceWords(self):
      subChar = bytes.fromhex('1A')

      for index in range(0, len(PASSAGES) + 1):
         key = str(index)
         p = PASSAGES[key]
         m = STORY_MAP[key]
         print(p['pt'])
         text = ''.join(ch for ch in test if ch not in exclude)
         words += text.split()

         if p['en'] == True:
            print("Ending: " + str(p['en']))
         else:
            if len(p['cs']) == 1:
               print("Auto forward")
            else:
               for index in range(0, len(p['cs'])):
                  print(" - " + p['cs'][index])


   def BuildDictionary(self, nodeMap, passages):
      exclude = set(string.punctuation)
      # Don't want to remove puncuation from INSIDE words.
      # There a better way to do this?
      exclude.remove("'")
      words = []

      #print passages
      for index in range(0, len(passages)):
         key = str(index)
         p = passages[key]
         m = nodeMap[key]

         #print p['pt']

         text = self.translate_unicode(''.join(ch for ch in p['pt'] if ch not in exclude))
         words += text.split()

         if p['en'] == False:
            if len(p['cs']) == 1 and p['cs'][0] == "*":
               print("Auto forward from " + key + "...")
            else:
               for index in range(0, len(p['cs'])):
                  text = ''.join(ch for ch in p['cs'][index] if ch not in exclude)
                  text = self.translate_unicode(text)
                  words += text.split()

         for word in words:
            # See if the word meets the minimum.
            if len(word) < WORD_LEN_MIN:
               continue
            # See if the word is already in the map.
            if word not in WORD_MAP:
               #print "NEW WORD: " + word + ", size: " + str(len(word))
               # First offset is zero.
               offset = 0
               if len(WORD_ORDER):
                  # The offset is the previous offset + the length of the previous word
                  # multiplied by bytes per word, plus 1 byte for the delimiter.
                  offset = WORD_MAP[WORD_ORDER[-1]] + (len(WORD_ORDER[-1]) * CHAR_BYTE_SIZE) + 1
               # Add the word to the map with it's byte offset.
               WORD_MAP[word] = offset
               # Add to frequency map.
               WORD_FREQUENCY[word] = 1
               # Add the word to the list so we know their order
               WORD_ORDER.append(word);
            else:
               WORD_FREQUENCY[word] += 1
               #print "OLD WORD: " + word + ", offset: " + str(WORD_MAP[word]) + ", freq: " + str(WORD_FREQUENCY[word])

      # Generate bytearray of word map.
      wordArray = bytearray()
      for word in WORD_ORDER:
         wordArray += bytearray(word)
         wordArray += bytes.fromhex('00')

      # Calculate size, see if all words will fit in 2 byte offsets.
      if len(wordArray) > 65535:
         print("[WARN] This story requires 3 byte offset addressing to hold all words.")

      # Calculate space savings.
      totalSavings = 0
      for word in WORD_ORDER:
         savings = WORD_FREQUENCY[word] * (CHAR_BYTE_SIZE * len(word) - OFFSET_ADDR_SIZE) - CHAR_BYTE_SIZE * len(word) - 1
         #print word + " used " + str(WORD_FREQUENCY[word]) + " times, saving " + str(savings) + " bytes."
         print(word)
         totalSavings += savings
         print(totalSavings)
      print("Number of Words:     " + str(len(WORD_MAP)))
      print("Dictionary Size:     " + str(len(wordArray)))
      print("Char Byte Size:      " + str(CHAR_BYTE_SIZE))
      print("Offset Address Size: " + str(OFFSET_ADDR_SIZE))
      print("Total Byte Savings:  " + str(totalSavings))


   def GenerateHeader(self, language, title, subtitle, author, pubdate, credits, contact, binVer, storyVer, flags, storySize, variableCount):
      print("Generating Story Header...")
      # Verify data first.

      # Language Max - 4 bytes
      if len(language) > LANG_MAX:
         print("Language longer than " + LANG_MAX + " bytes: " + language)
         return False

      # Title Max - 64 bytes
      if len(title) > TITLE_MAX:
         print("Title longer than " + TITLE_MAX + " bytes: " + title)
         return False

      # Subtitle Max - 32 bytes
      if len(subtitle) > SUBTITLE_MAX:
         print("Subtitle longer than " + SUBTITLE_MAX + " bytes: " + subtitle)
         return False

      # Author Max - 48 bytes
      if len(author) > AUTHOR_MAX:
         print("Author longer than " + AUTHOR_MAX + " bytes: " + author)
         return False

      # Credits Max - 80 bytes
      if len(credits) > CREDITS_MAX:
         print("Credits longer than " + CREDITS_MAX + " bytes: " + credits)
         return False

      # Contact Max - 128 bytes
      if len(contact) > CONTACT_MAX:
         print("Contact longer than " + CONTACT_MAX + " bytes: " + contact)
         return False

      data = bytearray()

      # Header size.
      #headerSize = 394 # with hex UUID
      headerSize = 414 # with string UUID

      # Add the start of header - 1 byte
      data += bytes.fromhex('01')

      # Binary Version - 3 bytes
      parts = [int(x) for x in binVer.split('.')]
      if len(parts) != 3:
         print("Binary version invalid: " + binVer)
         return False
      data += parts[0].to_bytes(1, byteorder='big')
      data += parts[1].to_bytes(1, byteorder='big')
      data += parts[2].to_bytes(1, byteorder='big')

      # Generate the UUID
      m = hashlib.md5()
      m.update((author + title).encode('utf-8'))
      storyUuid = uuid.UUID(m.hexdigest())
      print("IFID: " + str(storyUuid))
      #data += storyUuid.bytes_le # little endian hex
      data += bytes(str(storyUuid).encode('utf-8'))

      # Flags - 4 bytes
      flagOne = ""
      # Variable Txt - Logic - Images - Ending Quality - Points - Family Friendly Rsvd x 2
      # 0x80           0x40    0x20     0x10             0x08     0x04
      if flags['variable_text']:
         flagOne += '1'
      else:
         flagOne += '0'

      if flags['logic']:
         flagOne += '1'
      else:
         flagOne += '0'

      if flags['images']:
         flagOne += '1'
      else:
         flagOne += '0'
      
      if flags['ending_quality']:
         flagOne += '1'
      else:
         flagOne += '0'
      
      if flags['points']:
         flagOne += '1'
      else:
         flagOne += '0'
      
      if flags['family_friendly']:
         flagOne += '1'
      else:
         flagOne += '0'
      
      # Add attribute padding.
      flagOne += "00"
      data += bitarray.bitarray(flagOne)

      # flagOne = int('00000000', 2)
      # data += bytes(flagOne)

      # Retry - Monospace - Multiplayer - Hide Used - Rsvd x 4
      # 0x80    0x40        0x20          0x10
      flagTwo = ""
      if flags['retry']:
         flagTwo += '1'
      else:
         flagTwo += '0'

      if flags['monospace']:
         flagTwo += '1'
      else:
         flagTwo += '0'

      # Add attribute padding.
      flagTwo += "000000"
      #data += bytes(int(flagTwo, 2))
      data += bitarray.bitarray(flagTwo)

      # flagTwo = int('10000000', 2)
      # data += bytes(flagTwo)

      # Rsvd x 8
      # 0x80 - 0x00
      #flagThree = int('00000000', 2)
      #data += bytes(flagThree)
      data += bitarray.bitarray('00000000')
      
      # Rsvd x 8
      # 0x80 - 0x00
      #flagFour = int('00000000', 2)
      #data += bytes(flagFour)
      data += bitarray.bitarray('00000000')

      # Story byte size - 4 bytes - Little Endian - Unsigned Long
      data += bytearray(struct.pack('<L', storySize + headerSize))

      print("Total Binary Size: " + str(storySize + headerSize))

      # Story Version - 3 bytes
      parts = [int(x) for x in storyVer.split('.')]
      if len(parts) != 3:
         print("Story version invalid: " + storyVer)
         return False
      data += parts[0].to_bytes(1, 'big')
      data += parts[1].to_bytes(1, 'big')
      data += parts[2].to_bytes(1, 'big')

      # Currently unused - 1 byte
      rsvd = 0
      data += rsvd.to_bytes(1, 'big')

      # Language Code - 4 bytes
      langData = bytearray(b'\0' * LANG_MAX)
      langData[0:len(language)] = bytearray(language.encode())[:]
      data += langData

      # Title - 64 bytes
      titleData = bytearray(b'\0' * TITLE_MAX)
      titleData[0:len(title)] = bytearray(title.encode())[:]
      data += titleData

      # Subtitle - 32 bytes
      subtitleData = bytearray(b'\0' * SUBTITLE_MAX)
      subtitleData[0:len(subtitle)] = bytearray(subtitle.encode())[:]
      data += subtitleData

      # Author - 48 bytes
      authorData = bytearray(b'\0' * AUTHOR_MAX)
      authorData[0:len(author)] = bytearray(author.encode())[:]
      data += authorData

      # Credits - 80 bytes
      creditsData = bytearray(b'\0' * CREDITS_MAX)
      creditsData[0:len(credits)] = bytearray(credits.encode())[:]
      data += creditsData

      # Contact - 128 bytes
      contactData = bytearray(b'\0' * CONTACT_MAX)
      contactData[0:len(contact)] = bytearray(contact.encode())[:]
      data += contactData

      # Published Datetime - 4 bytes - Little Endian - Unsigned Long
      
      # Split the utc offset part
      timestamp = 0
      if pubdate != "":
         naive_time_str, offset_str = pubdate[:-5], pubdate[-5:]
         naive_dt = datetime.datetime.strptime(naive_time_str, '%Y-%m-%d')

         # Parse the utc offset
         offset = int(offset_str[-4:-2])*60 + int(offset_str[-2:])
         if offset_str[0] == "-":
            offset = -offset
         dt = naive_dt.replace(tzinfo = FixedOffset(offset))
         timestamp = (dt - datetime.datetime(1970, 1, 1, tzinfo = pytz.utc)).total_seconds()
         #print(timestamp)
         
         # Old code using current time for publish.
         #timestamp = calendar.timegm(time.gmtime())

      # Pack the pubdate timestamp into the data blob.
      data += bytearray(struct.pack('<L', int(timestamp)))

      # Variable Count byte size - 2 bytes - Little Endian - Unsigned Short
      data += bytearray(struct.pack('<H', variableCount))

      if len(data) != headerSize:
         print("Story Header wrong size: " + str(len(data)))
         return False

      return data

   def WrapString(self, wrapStr, columnLen):
      index = 0
      lengthLeft = len(wrapStr)
      newStr = ""
      breakChar = '\n'
      charIndent = 2
      indented = False
      while lengthLeft > columnLen:
         if wrapStr[index + columnLen] == ' ':
            newStr += wrapStr[index:index + columnLen]
            newStr += breakChar
            index += columnLen + 1
            lengthLeft -= columnLen + 1
         else:
            result = wrapStr.rfind(' ', index, index + columnLen)
            if result < 0:
               newStr += wrapStr[index:index + columnLen]
               newStr += breakChar
               index += columnLen
               lengthLeft -= columnLen
            else:
               newStr += wrapStr[index:result]
               newStr += breakChar
               lengthLeft -= (result - index) + 1
               index = result + 1
         # Change the column length after the first loop in order to indent the rest.
         for i in range(0, charIndent):
            newStr += " "
         if not indented:
            columnLen = columnLen - charIndent
            indented = True
      newStr += wrapStr[index:]
      return newStr

   def CreateMapFile(self, nodeMap, path):
      #try:
      #	os.makedirs(path)
      #except OSError, e:
      #	if not os.path.exists(path):
      #		raise
      try:
         file = open(path, 'w')
      except IOError:
         print("[ERROR] Failed to open file: " + path)
         return False

      #jsonPsg = json.dumps(passage, sort_keys=True, indent=4)
      jsonPsg = json.dumps(nodeMap, sort_keys=True)
      file.write(jsonPsg)

      #############
      # Can't use json anymore, new CSV & colon method.
      #mapStr = ""
      #for key in nodeMap:
      #	if type(nodeMap[key]) is list:
      #		mapStr += key + ":"
      #		for item in nodeMap[key]:
      #			mapStr += item + ":"
      #		mapStr = mapStr[0:-1] + ","
      #mapStr = mapStr[0:-1]
      #file.write(mapStr)
      #############

      file.close()
      return True

   def translate_unicode(self, to_translate):
      table = {
         ord('’'): '\'',
         ord('‘'): '\'',
         ord('‛'): '\'',
         ord('’'): '\'',
         ord('“'): '"',
         ord('”'): '"',
         ord('‟'): '"',
         ord('„'): ',,',
         ord('›'): '>',
         ord('‹'): '<',
         ord('‧'): '.',
         ord('․'): '.',
         ord('‥'): '..',
         ord('…'): '...',
         ord('ä'): 'ae',
         ord('ö'): 'oe',
         ord('ü'): 'ue',
         ord('ß'): None,
         ord('—'): '-',
      }
      #s = to_translate.decode('utf8')
      return to_translate.translate(table).encode('ascii', 'ignore')

   def CreatePassageFile(self, nodeValue, path, update, force, nodeMap, passage = None, json = False):
      if json == False:
         try:
            os.makedirs(path)
         except OSError as e:
            if not os.path.exists(path):
               raise
         pointsPath = os.path.join(path, "P")
         self.WriteToFile(pointsPath, bytearray([passage["pp"]]))
         textPath = os.path.join(path, "T")

         passage["pt"] = self.translate_unicode(passage["pt"])

         try:
            self.WriteToFile(textPath, passage["pt"])
         except IOError as e:
            print("Error exporting passage text for passage: " + passage)

         endingPath = os.path.join(path, "E");
         if passage["en"]:
            self.WriteToFile(endingPath, bytearray([1, passage["eq"], int(passage["cc"])]))
         else:
            data = bytearray([0])
            #self.WriteToFile(endingPath, bytearray([0]))
            if nodeValue == "0":
               data.append(passage["cp"])
               data += bytearray(struct.pack('>H', passage["ps"]))
               #self.WriteToFile(endingPath, bytearray([passage["cp"]]))
               #print len(bytearray([passage["cp"]]))
               #self.WriteToFile(endingPath, bytearray(struct.pack('H', passage["ps"])))
               #print len(bytearray(struct.pack('H', passage["ps"])))
            self.WriteToFile(endingPath, data)

            appendStr = "-"
            if passage["cs"][0] == "*":
               appendStr = "*"

            choiceTestPath = os.path.join(path, "C")
            self.WriteToFile(choiceTestPath, appendStr)

            numberPath = os.path.join(path, "N")
            self.WriteToFile(numberPath, bytearray([len(nodeMap[nodeValue])]))
            #choiceTestPath = os.path.join(path, "C")
            #self.WriteToFile(choiceTestPath, choiceStr)

            i = 0
            for node in nodeMap[nodeValue]:
               print("Choice: " + passage["cs"][i])
               if passage["cs"][i] != "*":
                  choiceStr = str(i+1) + "." + self.translate_unicode(passage["cs"][i])
               else:
                  choiceStr = str(i+1) + "." + passage["cs"][i]
               choicePath = os.path.join(path, str(i));
               i += 1
               # Places for maximum number of passages. 3 = 999 passages
               maxBytes = 3
               k = 0
               passageStr = ""
               for n in node:
                  passageStr += n
                  k += 1
               while k < maxBytes:
                  passageStr += '-'
                  k += 1
               passageStr += choiceStr
               self.WriteToFile(choicePath, passageStr)
               #self.WriteToFile(choicePath, bytearray([int(node)]))
      return True

   def WriteToFile(self, path, data):
      #path = path + ".txt"
      try:
         file = open(path, 'wb')
      except IOError:
         print("[ERROR] Failed to write file: " + path)
         file.close()
         return False

      #file.write(data)
      try:
         file.write(data)
      except UnicodeEncodeError as e:
         print("[ERROR] Failed to write character ("+ e.object[e.start:e.end] + ") of: " + e.object)
      file.close()

   def LoadPassageJson(self, path):
      try:
         file = open(path, 'r')
      except IOError:
         print("[ERROR] Unable to open passage: " + path)
         file.close()
         return False

      jsonStr = file.read()
      file.close()
      return json.loads(jsonStr)

   def CreateGenericPassage(self):
      passage = {}
      i = 0
      for item in PASSAGE_KEYS:
         if PASSAGE_TYPES[i] == 'bool':
            passage[item] = False
         elif PASSAGE_TYPES[i] == 'string':
            passage[item] = "string value"
         elif PASSAGE_TYPES[i] == 'int':
            passage[item] = 1
         elif PASSAGE_TYPES[i] == 'array':
            passage[item] = ["item one", "item two"]
         i += 1
      return passage

#
# Helper functions
#

def version_compare(version1, version2):
   return cmp(normalize_version_num(version1), normalize_version_num(version2))

def normalize_version_num(v):
   return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]

#
# Main
#

if __name__ == '__main__':
   main()
