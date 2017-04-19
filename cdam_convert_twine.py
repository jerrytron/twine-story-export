#!/usr/bin/env python
# encoding=utf8

import os
import re
import sys
import struct
import pprint
import random
import argparse
import datetime
import tiddlywiki as tiddly
import cdam_gen_files as gen

reload(sys)
sys.setdefaultencoding('utf8')

VERSION = "1.0"

BINARY_VER = "1.0.0"

# For holding binary variable keys and values.
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
LINEAR = False
HTML = False
SEED = None

PP = pprint.PrettyPrinter(indent = 4)

kAppend = "<append>"
kContinue = "<continue>"
kContinueCopy = u'Continue...'
kGotoTempTag = "-GOTO-"

class CDAMParser(argparse.ArgumentParser):
	def error(self, message):
		sys.stderr.write('error: %s\n' % message)
		self.print_help()
		sys.exit(2)

class CDAMTwine(tiddly.Tiddler):
	def GetPassages(self):
		return self.tiddlers

def main():
	global STORY_TITLE
	global STORY_AUTHOR
	global STORY_SUBTITLE
	global STORY_CREDITS
	global STORY_CONTACT
	global STORY_LANGUAGE
	global STORY_VERSION
	global LINEAR
	global HTML

	# To Make a Linear Story:
	# python ./cdam_convert_twine.py --title

	parser = CDAMParser(version='1.0', description='CDAM Twine Source Code Converter')
	parser.add_argument('--dirname', default='NONE', action='store', help='Directory name for story on the file system.')
	parser.add_argument('--title', default='Untitled', action='store', help='The story title.')
	parser.add_argument('--subtitle', default='NONE', action='store', help='The story subtitle.')
	parser.add_argument('--author', default='Anonymous', action='store', help='The author of the story.')
	parser.add_argument('--credits', default='', action='store', help='Additional story credits.')
	parser.add_argument('--contact', default='Follow @choosatron online!', action='store', help='Misc contact info.')
	parser.add_argument('--lang', default='eng', action='store', help='Up to four character language code.')
	parser.add_argument('--ver', default='0.0.0', action='store', help='Story version in three parts, x.x.x')
	parser.add_argument('--source', default='', action='store', help='The Twine source code file.')
	parser.add_argument('--output', default='./', action='store', help='The location to create the output files.')
	parser.add_argument('--filename', default='', action='store', help='The output filename.')
	parser.add_argument('--json', action='store_true', help='Output as a JSON text file.')
	parser.add_argument('--linear', action='store_true', help='Output as a linear text file for humans.')
	parser.add_argument('--html', action='store_true', help='Output as html document.')
	parser.add_argument('--randseed', default='', action='store', help='Optional seed to control random output.')
	parser.add_argument('--binary', action='store_true', help='Output as a CDAM binary for the Choosatron v2.')
	parser.add_argument('--verbose', action='store_true', help='Print additional info, including warnings.')
	parser.add_argument('--operation', action='store_true', help='Output operations file too for debugging.')
	#parser.add_argument('--update', action='store_true', help='Attempt to safely add to/update existing files without damaging existing data.')
	#parser.add_argument('--force', action='store_true', help='Overwrite files that already exist.')
	args = parser.parse_args()

	STORY_SUBTITLE = args.subtitle
	STORY_CREDITS = args.credits
	STORY_CONTACT = args.contact
	STORY_LANGUAGE = args.lang
	STORY_VERSION = args.ver

	if args.randseed:
		SEED = int(args.randseed)
		random.seed(SEED)
	else:
		SEED = datetime.datetime.now().microsecond
		#print "Random Seed for " + args.title + ": " + str(SEED)
		random.seed(SEED)

	LINEAR = args.linear
	HTML = args.html
	if HTML:
		LINEAR = True

	# Uncomment to override output and place wherever source was.
	#args.output = os.path.dirname(args.source)

	VERBOSE = args.verbose

	if VERBOSE:
		print args.title

	storyWiki = LoadSource(args.source)
	if storyWiki == False:
		return
	result = BuildCDAMStory(storyWiki)
	if result == False:
		return

	if args.dirname.upper() in PASSAGES:
		print "[ERROR] Value of --dirname can't be the same as a passage title. Passage already exists named: " + args.dirname.upper()
		return

	SimplifyNaming()
	genFile = gen.CDAMGenFiles()

	if args.binary == True:
		if args.title != "Untitled":
			STORY_TITLE = args.title

		if args.author != "Anonymous":
			STORY_AUTHOR = args.author

		# Generate Story Body
		storyBody = genFile.GenerateBody(STORY_MAP, PASSAGES, VARIABLES)
		if storyBody == False:
			return

		# Generate Story Header
		storyHeader = genFile.GenerateHeader(args.lang, args.title, args.subtitle, args.author, args.credits, args.contact, BINARY_VER, args.ver, len(storyBody), len(VARIABLES))
		if storyHeader == False:
		 	return

		bookPath = STORY_TITLE.lower().replace(" ", "_") + "_BIN.dam"
		if args.filename != "":
			bookPath = args.filename + "_BIN.dam"
		bookPath = os.path.join(args.output, bookPath)


		if os.path.exists(bookPath):
			os.remove(bookPath)
		genFile.WriteToFile(bookPath, storyHeader + storyBody)

		if args.operation:
			opPath = STORY_TITLE.lower().replace(" ", "_") + "_OPS.dam"
			if args.filename != "":
				opPath = args.filename + "_OPS.dam"
			opPath = os.path.join(args.output, opPath)
			opData = bytearray()
			opData += bytearray(struct.pack('<H', TOTAL_OPS))
			opData += OPERATION_TEST
			genFile.WriteToFile(opPath, opData)
	elif args.linear == True:
		if args.title != "Untitled":
			STORY_TITLE = args.title

		if args.author != "Anonymous":
			STORY_AUTHOR = args.author

		if HTML:
			bookPath = STORY_TITLE.lower().replace(" ", "_") + "_LINEAR.html"
			if args.filename != "":
				bookPath = args.filename + "_LINEAR.html"
		else:
			bookPath = STORY_TITLE.lower().replace(" ", "_") + "_LINEAR.txt"
			if args.filename != "":
				bookPath = args.filename + "_LINEAR.txt"
		bookPath = os.path.join(args.output, bookPath)

		book = ""

		if HTML:
			# Look for an HTML header to insert.
			sourcePath = os.path.dirname(args.source)
			headerPath = os.path.join(sourcePath, "header.txt")
			try:
				file = open(headerPath, 'r')
				book += file.read()
			except IOError:
				print "[WARNING] No HTML header found at: " + headerPath

		book += "Title: " + STORY_TITLE + "\nSubtitle: " + STORY_SUBTITLE + "\nAuthor: " + STORY_AUTHOR
		book += "\nCredits: " + STORY_CREDITS + "\nContact: " + STORY_CONTACT + "\nLanguage: " + STORY_LANGUAGE + "\nVersion: " + STORY_VERSION + "\nSeed: " + str(SEED) + "\n\n\n"

		psgList = []
		newMap = {}
		allKeys = PASSAGES.keys()

		key = "0"
		p = PASSAGES[key]
		psgList.append(p)
		allKeys.remove(key)
		newMap[key] = key

		index = 0

		while len(allKeys) > 0:
			index += 1
			if "choices" in p and len(p["choices"]) == 1 and p["choices"][0]["link"] in allKeys:
				p = PASSAGES[p["choices"][0]["link"]]
				key = p["key"]
				# Map from old to new index.
				newMap[key] = str(index)
				if key in allKeys:
					allKeys.remove(key)
				psgList.append(p)
			else:
				key = random.choice(allKeys)
				# If this passage has a single entrance, that passage should be
				# put in first.
				if "ik" in PASSAGES[key]:
					while len(PASSAGES[key]["ik"]) == 1:
						# Keep tracing back until we find the first passage in a series
						# of single paths, or until we hit a passage already used.
						if PASSAGES[key]["ik"][0] in allKeys:
							key = PASSAGES[key]["ik"][0]
						else:
							break
				if key in allKeys:
					allKeys.remove(key)
				p = PASSAGES[key]
				newMap[key] = str(index)
				psgList.append(p)

		index = 0
		for psg in psgList:
			book += linearPassageText(psg, newMap)
			index += 1
			if index < len(psgList):
				book += "\n\n\n"


		# Look for an HTML footer to insert.
		if HTML:
			sourcePath = os.path.dirname(args.source)
			footerPath = os.path.join(sourcePath, "footer.txt")
			try:
				file = open(footerPath, 'r')
				book += file.read()
				#print book
			except IOError:
				print "[WARNING] No HTML footer found at: " + footerPath


		if os.path.exists(bookPath):
			os.remove(bookPath)
		genFile.WriteToFile(bookPath, book)
	else:
		result = False;
		if args.json == False:
			result = genFile.UpdateManifest(args.output, args.title, args.dirname, args.author, args.json)
			if result == False:
				print "[ERROR] Failed to update manifest."
		else:
			result = args.dirname

		result = genFile.BuildCDAMStory(result, STORY_MAP, PASSAGES, args.output, args.title, args.author, args.json)
		if result == False:
			print "[ERROR] Failed to build story."

	print "Complete!"
	#print STORY_MAP
	#print PASSAGES

def linearPassageText(aPassage, aMap):
	global HTML

	psgText = ""
	goto = " (go to "
	key = aMap[aPassage["key"]]

	if HTML:
		psgText += "<p class='paragraph'><span class='number'>" + "[" + key + "] </span>" + aPassage['pt'] + "</p>"
		psgText += "\n"
	else:
		psgText += "[" + key + "] " + aPassage['pt']

	if aPassage['en'] == True:
		psgText += "\n--- THE END ---"

		#if aPassage['eq'] == 1:
		#	psgText += "\n* - THE END"#* Oh no! Better luck next adventure. * - THE END"
		#elif aPassage['eq'] == 2:
		#	psgText += "\n** - THE END"#** I'm sure you can do better. ** - THE END"
		#elif aPassage['eq'] == 3:
		#	psgText += "\n*** - THE END"#*** You win some, you lose some. *** - THE END"
		#elif aPassage['eq'] == 4:
		#	psgText += "\n**** - THE END"#**** Not too bad! **** - THE END"
		#elif aPassage['eq'] == 5:
		#	psgText += "\n***** - THE END"#***** Congratulations! You sure know your stuff. ***** - THE END"
	else:
		choiceText = ""
		if HTML == False:
			# Add a delimeter so we know it is done
			choiceText += "\n---"

		for choice in aPassage['choices']:
			m = re.search(kGotoTempTag, psgText)

			if HTML:
				if psgText[m.start() - 1] == '\n':
					choiceText += ("<span class='choice-title choice-standalone'>" + choice['text'] + "</span>" + "<span class='goto'>" + goto + aMap[choice['link']] + ")</span>")
				else:
					choiceText += ("<span class='choice-title'>" + choice['text'] + "</span>" + "<span class='goto'>" + goto + aMap[choice['link']] + ")</span>")
			else:
				choiceText += ("\n- " + choice['text'] + goto + aMap[choice['link']] + ")")

			psgText = re.sub(kGotoTempTag, choiceText, psgText, 1);
			choiceText = ""
	return psgText

def linearPassageTextFull(aPassages, aStoryMap, aKey):
	psgText = ""
	goto = " (go to "
	p = aPassages[aKey]
	m = aStoryMap[aKey]
	psgText += "[" + aKey + "] " + p['pt']
	# Add a delimeter so we know it is done
	psgText += "\n---"

	if p['en'] == True:
		if p['eq'] == 1:
			psgText += "\n* - THE END"#* Oh no! Better luck next adventure. * - THE END"
		elif p['eq'] == 2:
			psgText += "\n** - THE END"#** I'm sure you can do better. ** - THE END"
		elif p['eq'] == 3:
			psgText += "\n*** - THE END"#*** You win some, you lose some. *** - THE END"
		elif p['eq'] == 4:
			psgText += "\n**** - THE END"#**** Not too bad! **** - THE END"
		elif p['eq'] == 5:
			psgText += "\n***** - THE END"#***** Congratulations! You sure know your stuff. ***** - THE END"
	else:
		if len(p['cs']) == 1:
			psgText += ("\n- " + p['cs'][0] + goto + m[0] + ")")
		else:
			for index in range(0, len(p['cs'])):
				psgText += ("\n- " + p['cs'][index] + goto + m[index] + ")")
	return psgText

def twineBuild(storySource, path, storyDir, title, author):
	STORY_MAP.clear()
	PASSAGES.clear()

	result = BuildCDAMStory(storySource)
	if result == False:
		return

	SimplifyNaming()
	genFile = gen.CDAMGenFiles()

	result = genFile.UpdateManifest(path, title, storyDir, author)
	if result == False:
		print "[ERROR] Failed to update manifest."

	result = genFile.BuildCDAMStory(storyDir, STORY_MAP, PASSAGES, path, title, author)
	if result == False:
		print "[ERROR] Failed to build story."

def LoadSource(path):
	try:
		file = open(path, 'r')
	except IOError:
		print "[ERROR] File not found: " + path
		return False

	sourceStr = file.read()
	file.close()

	# Start reading from the first ':' character
	index = 0
	for char in sourceStr:
		if char == ':':
			break
		index += 1
	sourceStr = sourceStr[index:]

	wiki = tiddly.TiddlyWiki()
	wiki.addTwee(sourceStr)
	return wiki

def BuildCDAMStory(wiki):
	global STORY_TITLE
	global STORY_AUTHOR
	global LINEAR

	for key in wiki.tiddlers.keys():
		upKey = key.strip().upper()
		if upKey not in wiki.tiddlers.keys():
			wiki.tiddlers[upKey] = wiki.tiddlers[key]
			del wiki.tiddlers[key]

	for key in wiki.tiddlers:
		if wiki.tiddlers[key].title == "StoryTitle":
			if STORY_TITLE == "":
				STORY_TITLE = wiki.tiddlers[key].text
			continue
		if wiki.tiddlers[key].title == "StorySubtitle":
			continue
		if wiki.tiddlers[key].title == "StoryAuthor":
			if STORY_AUTHOR == "":
				STORY_AUTHOR = wiki.tiddlers[key].text
			continue

		print "Passage: " + key
		passage = ParseForAttributes(wiki.tiddlers[key].tags)
		if passage == False:
			continue
		# Is this the starting passage?
		if key == "START":
			if "ps" not in passage:
				passage["ps"] = 0
			if "cp" not in passage:
				passage["cp"] = 0
			if "sv" not in passage:
				passage["sv"] = "1.0"
		else:
			if "ps" in passage:
				if VERBOSE:
					print "[WARNING] Only set perfect score ('ps' or 'perfect') in the story passage titled 'Start'."
				del passage["ps"]
			if "cp" in passage:
				if VERBOSE:
					print "[WARNING] Only set continue penalty ('cp' or 'penalty') in the story passage titled 'Start'."
				del passage["cp"]
			if "sv" in passage:
				if VERBOSE:
					print "[WARNING] Only set story version ('sv' or 'version') in the story passage titled 'Start'."
				del passage["sv"]

		passage["pv"] = VERSION
		if "pp" not in passage:
			passage["pp"] = 0
		rss = wiki.tiddlers[key].toRss()
		choicePairs = ParseForChoices(rss.description)
		print choicePairs
		PP.pprint(choicePairs)
		passage["pt"] = ParseForBody(rss.description)

		if type(choicePairs) is bool:
			# No choices in this passage.
			if choicePairs == True:
				if "eq" not in passage:
					if VERBOSE:
						print "[WARNING] Ending quality 'eq' not set for " + key
					# Default to average.
					passage["eq"] = 3
				STORY_MAP[key] = passage["eq"]
				passage["en"] = True
				if "cc" not in passage:
					passage["cc"] = True
			else:
				print "[ERROR] Failed to parse for choices."
				return False
		if type(choicePairs) is list:
			nodes = []
			choices = []
			for item in choicePairs:
				nodes.append(item['link'].strip().upper())
				choices.append(item['text'])
			if ValidateChoices(wiki.tiddlers, nodes) == False:
				print "[ERROR] Failed to validate choices for node."
				return False
			else:
				STORY_MAP[key] = nodes
			passage["en"] = False
			#passage["cs"] = choices
			#passage["ck"] = nodes
			passage["choices"] = choicePairs
		print "Validating passage for node " + key
		if ValidatePassage(passage) == False:
			print "[ERROR] Failed to validate passage."
			return False
		else:
			PASSAGES[key] = passage
			#print PASSAGES

def ParseOperation(opParts, iteration):
	global REPORT

	data = bytearray()

	REPORT += "( "
	types = ""
	leftName = ""
	rightName = ""
	command = opParts.pop(0)
	leftType = opParts.pop(0)

	leftValue = bytearray()
	rightValue = bytearray()

	#print "Command: " + command
	#print "LeftType: " + leftType

	if leftType == "cmd":
		types += "0011"
		leftValue = ParseOperation(opParts, iteration + 1)
		REPORT += " " + command + " "
	else:
		tempValue = opParts.pop(0)
		if leftType == "var":
			#print tempValue
			leftName = tempValue
			types += "0010"
			if leftName not in VARIABLES:
				VARIABLES[leftName] = len(VARIABLES)
			REPORT += leftName + "[" + str(VARIABLES[leftName]) + "] " + command + " "
			#print "Var #: " + str(VARIABLES[leftName])
			leftValue = bytearray(struct.pack('<H', VARIABLES[leftName]))
		else:
			types += "0001"
			leftValue = bytearray(struct.pack('<H', int(tempValue)))
			REPORT += str(tempValue) + " " + command + " "
			#print str(leftValue)


	rightType = opParts.pop(0)

	#print "RightType: " + rightType

	rightPrintVal = 0
	if rightType == "cmd":
		types += "0011"
		rightValue = ParseOperation(opParts, iteration + 1)
	else:
		tempValue = opParts.pop(0)
		if rightType == "var":
			#print tempValue
			rightName = tempValue
			types += "0010"
			if rightName not in VARIABLES:
				VARIABLES[rightName] = len(VARIABLES)
			#print "Index: " + str(VARIABLES[rightName])
			rightValue = bytearray(struct.pack('<H', VARIABLES[rightName]))
		else:
			types += "0001"
			rightValue = bytearray(struct.pack('<H', int(tempValue)))
			rightPrintVal = tempValue
			#print str(rightValue)

	data += chr(int(types, 2))

	if command == "equal" or command == "==":
		data += chr(0x01)
	elif command == "not_equal" or command == "!=":
		data += chr(0x02)
	elif command == "greater" or command == ">":
		data += chr(0x03)
	elif command == "less" or command == "<":
		data += chr(0x04)
	elif command == "greater_equal" or command == ">=":
		data += chr(0x05)
	elif command == "less_equal" or command == "<=":
		data += chr(0x06)
	elif command == "and":
		data += chr(0x07)
	elif command == "or":
		data += chr(0x08)
	elif command == "xor":
		data += chr(0x09)
	elif command == "nand":
		data += chr(0x0A)
	elif command == "nor":
		data += chr(0x0B)
	elif command == "xnor":
		data += chr(0x0C)
	elif command == "visible":
		data += chr(0x0D)
	elif command == "mod" or command == "%":
		data += chr(0x0E)
	elif command == "set" or command == "=":
		data += chr(0x0F)
	elif command == "plus" or command == "add" or command == "+":
		data += chr(0x10)
	elif command == "minus" or command == "-":
		data += chr(0x11)
	elif command == "multiply" or command == "mult" or command == "*":
		data += chr(0x12)
	elif command == "divide" or command == "/":
		data += chr(0x13)
	elif command == "rand" or command == "random":
		data += chr(0x14)
	elif command == "dice" or command == "roll":
		data += chr(0x15)
	elif command == "if":
		data += chr(0x16)

	if rightType == "var":
		REPORT += rightName + "[" + str(VARIABLES[rightName]) + "]"
	elif rightType == "raw":
		REPORT += str(rightPrintVal)

	REPORT += " )"
	data += leftValue
	data += rightValue

	return data

def ParseForAttributes(tags):
	global REPORT
	global OPERATION_TEST
	global TOTAL_OPS
	attributes = {}
	attributes["vu"] = []
	attributes["cvu"] = {}
	#attributes["cvu"]["totalBytes"] = 0
	attributes["cdc"] = {}
	for attr in tags:
		attr = attr.lower()
		if attr == "ignore":
			return False
		#print attr
		pair = attr.split(':')

		#if pair[0] == "vars":
		#	pair.pop(0)
		#	for var in pair:
		#		varSet = var.split('|')
		#		VARIABLES[varSet[0]] = { "default" : varSet[1], "index" : len(VARIABLES) }

		if pair[0] == "vu":
			print pair
			pair.pop(0)
			REPORT = ""
			data = bytearray()
			data = ParseOperation(pair, 0)
			print ":".join("{:02x}".format(ord(chr(c))) for c in data)
			OPERATION_TEST += data
			TOTAL_OPS += 1

			print REPORT
			#updates = { "operation" : pair[1], "leftType" : pair[2], "leftValue" : pair[3], "rightType" : pair[4], "rightValue" : pair[5] }
			#if updates["leftType"] == "var":
			#	if updates["leftValue"] not in VARIABLES:
			#		print "New var added: " + updates["leftValue"]
			#		VARIABLES[updates["leftValue"]] = { "default" : 0, "index" : len(VARIABLES) }
			#if updates["rightType"] == "var":
			#	if updates["rightValue"] not in VARIABLES:
			#		print "New var added: " + updates["rightValue"]
			#		VARIABLES[updates["rightValue"]] = { "default" : 0, "index" : len(VARIABLES) }
			attributes["vu"].append(data)

		elif pair[0] == "choice":
			pair.pop(0)
			index = int(pair.pop(0)) - 1
			if attributes["cvu"].setdefault(index, None) == None:
				attributes["cvu"][index] = { "data" : [], "totalBytes" : 0}
			opType = pair.pop(0)
			REPORT = ""
			data = bytearray()
			data = ParseOperation(pair, 0)
			OPERATION_TEST += data
			TOTAL_OPS += 1
			print REPORT
			#attributes["cvu"]["totalBytes"] = 0
			#components = { "valueOne" : pair[3], "operation" : pair[4], "valueTwoType" : pair[5], "valueTwo" : pair[6] }
			if opType == "vu": # Value updates
				#if attributes["cvu"].setdefault(index, None) == None:
					#print "Fresh Choice: " + str(index)
					#attributes["cvu"][index] = { "data" : [], "totalBytes" : 0}
					#attributes["cvu"][index]["data"] = bytearray()
					#attributes["cvu"][index]["totalBytes"] = 0
				attributes["cvu"][index]["data"].append(data)
				attributes["cvu"][index]["totalBytes"] += len(data)

			elif opType == "dc": # Display conditionals
				attributes["cdc"].setdefault(index, []).append(data)

		elif len(pair) == 2:
			# Set Default Values
			if pair[0] == "pp" or pair[0] == "points":
				attributes["pp"] = int(pair[1])
			elif pair[0] == "eq" or pair[0] == "quality":
				attributes["eq"] = int(pair[1])
			elif pair[0] == "cc" or pair[0] == "continue":
				if pair[1] in ['true', '1', 't']:
					attributes["cc"] = True
				elif pair[1] in ['false', '0', 'f']:
					attributes["cc"] = False
				else:
					if VERBOSE:
						print "[WARNING] Invalid boolean value provided for tag: " + pair[0]
			elif pair[0] == "ps" or pair[0] == "perfect":
				attributes["ps"] = int(pair[1])
			elif pair[0] == "cp" or pair[0] == "penalty":
				attributes["cp"] = int(pair[1])
			elif pair[0] == "lc" or pair[0] == "color":
				if VERBOSE:
					print "[WARNING] Color not currently supported."
				#attributes["lc"] = int(pair[1])
			elif pair[0] == "sn" or pair[0] == "sound":
				if VERBOSE:
					print "[WARNING] Sound not currently supported."
				#attributes["sn"] = int(pair[1])
			elif pair[0] == "sv" or pair[0] == "version":
					attributes["sv"] = pair[1]
	return attributes

def ParseForChoices(bodyText):
	global LINEAR
	global HTML

	# Cleanse choices of carriage returns.
	bodyText = bodyText.replace('\r', '\n')
	if HTML:
		bodyText = bodyText.replace('\n\n', '<br>\n')
	#else:
		#bodyText = bodyText.replace('\n\n', '\n')

	choices = []
	# Search for either [[Choice Text|Choice Key]] or [[Choice Key]] and warn about missing text.
	matchCount = len(re.findall(r"\n*\[\[([^\[\]|]+)(?:\|([\w\d\s]+))?\]\]", bodyText))

	for index in range(0, matchCount):
		m = re.search(r"\n*\[\[([^\[\]|]+)(?:\|([\w\d\s]+))?\]\]", bodyText)
	#for m in re.finditer(r"\[\[([^\[\]|]+)(?:\|([\w\d\s]+))?\]\]", text):
		# For [[Run away.|1B]], m.group(0) is whole match, m.group(1) = 'Run away.', and m.group(2) = '1B'
		# For [[Run away.]], same but there is no m.group(2)
		choice = {}
		choice['index'] = m.start()
		choice['length'] = m.end() - m.start()
		text = m.group(1)
		link = m.group(2)
		# No link means copy text & link text are the same.
		if not link:
			link = text

		# Link is meant for auto-jumping.
		if text.lower() == kAppend:
			if len(choices) == 0:
				# If only a choice key, label it for an auto jump to the passage.
				if LINEAR:
					text = "Continue..."
				else:
					text = "*"
			else:
				print "[ERROR] Can only have a single auto-jump choice per passage."
				return False
		elif text.lower() == kContinue:
			text = kContinueCopy

		choice['link'] = link.strip().upper()
		choice['text'] = text.strip()
		choices.append(choice)

		replaceChoices = ""
		if LINEAR:
			replaceChoices = kGotoTempTag

		bodyText = re.sub(r"\n*\[\[([^\[\]|]+)(?:\|([\w\d\s]+))?\]\]", replaceChoices, bodyText, 1)

	if len(choices) == 0:
		return True
	return choices

def ParseForBody(text):
	global LINEAR
	global HTML

	# Cleanse of carriage returns (but leave newlines!).
	#
	body = text
	body = body.replace('\r', '\n')

	if HTML:
		body = body.replace('\n\n', '<br>\n')
	#else:
		#body = body.replace('\n\n', '\n')

	replaceChoices = ""
	if LINEAR:
		replaceChoices = kGotoTempTag

	body = re.sub(r"\n*\[\[([^\[\]|]+)(?:\|([\w\d\s]+))?\]\]", replaceChoices, text)

	return body

def ValidateChoices(tiddlers, nodes):
	#print tiddlers
	for node in nodes:
		if node not in tiddlers:
			print tiddlers
			print "[ERROR] Choice key found without matching passage: " + node
			return False
	return True

def ValidatePassage(passage):
	if "cc" in passage:
		if passage["cc"] == True and passage["en"] == False:
			if VERBOSE:
				print "[WARNING] Continue flag useless if a passage isn't an ending. Setting False."
			passage["cc"] = False
		elif passage["cc"] == True and passage["eq"] == 5:
			#print "[WARNING] Continue flag should be false if ending quality is 5."
			passage["cc"] = False
	if passage["en"] == True and "eq" not in passage:
		print "[ERROR] Ending Quality (eq|quality) missing from ending passage."
		return False
	if "eq" in passage:
		if passage["eq"] > 5 or passage["eq"] < 1:
			print "[ERROR] Ending Quality (eq|quality) value outside range of 1-5."
			return False
	if passage["pp"] > 255 or passage["pp"] < 0:
		print "[ERROR] Ending Quality (eq|quality) value outside range of 0-255."
		return False

def SimplifyNaming():
	i = 1
	newMap = STORY_MAP.copy()
	STORY_MAP.clear()
	newPassages = PASSAGES.copy()
	PASSAGES.clear()

	for titleKey in newMap:
		upTitleKey = titleKey.strip().upper()
		if upTitleKey != "START":
			# Create a map from all passage titles to its new numbered title.
			TITLE_MAP[upTitleKey] = str(i)
			i += 1
		else:
			TITLE_MAP["START"] = "0"

	for titleKey in newMap:
		upTitleKey = titleKey.strip().upper()
		if type(newMap[upTitleKey]) is list:
			i = 0
			for val in newMap[upTitleKey]:
				# Links always referenced in uppercase.
				#print "HERE: " + titlekey + " : " + i
				newMap[upTitleKey][i] = TITLE_MAP[val.strip().upper()]
				i += 1
		STORY_MAP[TITLE_MAP[upTitleKey]] = newMap[upTitleKey]
		PASSAGES[TITLE_MAP[upTitleKey]] = newPassages[upTitleKey]
		PASSAGES[TITLE_MAP[upTitleKey]]['key'] = TITLE_MAP[upTitleKey]

	# Create array for all incoming links on a passage.
	for key in PASSAGES:
		psg = PASSAGES[key]
		if "choices" in psg and len(psg["choices"]) > 0:
			for choice in psg["choices"]:
				choice["link"] = TITLE_MAP[choice["link"].strip().upper()]
				psgKey = choice["link"].strip().upper()
				if "ik" not in PASSAGES[psgKey]:
					PASSAGES[psgKey]["ik"] = [""]
				PASSAGES[psgKey]["ik"].append(psg["key"])

if __name__ == '__main__':
	#global _UPDATE
	#global _FORCE
	main()