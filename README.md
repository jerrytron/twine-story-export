# twine-story-export
A repo for code that will import Twine source and export content in other formats.

Download and install Twine:

[macOS download](http://twinery.org/downloads/twine_1.4.2_osx.zip) - [Windows download](http://twinery.org/downloads/twine_1.4.2_win.exe)

__Note: This is possible with the downloadable version of Twine 2, but you need to install the 'Entweedle' plugin below (or another that allows Twee export, the original Twine source format).__

Alternatively, download and install Twine 2:

[macOS download](https://github.com/klembot/twinejs/releases/download/2.3.2/twine_2.3.2_macos.dmg) - [Windows download](https://github.com/klembot/twinejs/releases/download/2.3.2/twine_2.3.2_win.exe)

__Required plugin: [Illume - Proofing Tool w/ Twee Export](http://www.maximumverbosity.net/twine/Illume/)__

Once the plugin is installed and setup, from within the editor for a story, click on the title and select _View Proofing Copy_ from the list. Then select _Export Twee Source__ from the list in the upper left.

__Notes for Twine 2:__

This guide assumes exporting Twee source from Twine 1 where files are _.txt_ by default. Exporting form Illume defaults to _.tw_. You can either save as _.txt_ instead, or simply use the _.tw_ extention in the commands.

The exported source might include the following sections that (until I've tested) should be deleted:
```
:: UserScript[script]
/* twine-user-script-joiner */

:: UserStylesheet[stylesheet]
/* twine-user-stylesheet-joiner */
```

## Guidelines for a Choosatron Compatible Twine Story

1. You MUST have a _Start_ passage as your story beginning.
2. You must NOT have any passages that aren't part of the story, unless they are _StoryAuthor_ or _StoryTitle_. Those are special.
3. You should NOT have spaces or special characters in the titles of your passages.
4. In your passages, you should always have the body text first, followed by your choices.
5. For the Choosatron, you can have a maximum of ten choices per passage, but a maximum of four is optimal (looks better on the device as no combination key presses are required).
6. Think of a Choosatron as an arcade machine. Players generally find the stories more enjoyable if each passage is shorter on text, and the story allows them many choices. This is of course to taste.

__Note: I've never tried ANY of this on Windows...__

Here is an example using one of my stories. I've included the original Twine file and the source file exported (in the StoryTests folder). To export, open a Twine story and go to File -> Export -> Twee Source Code
Save it as a .txt file. This is the source file you feed the script.

## Generating a Linear Document (like a CYOA story)
This can be useful to verify that your binary conversion will work, and is a fun way to share a functional interactive fiction story in a linear (and printable) document.

__Note: You must have [pipenv](https://pipenv.pypa.io/en/latest/install/) installed to run this set of tools.__

If this is your first use, navigate a command line to the project folder and run: `pipenv install`

To start the python environment and use the tools, run: `pipenv shell`

```
./cdam_convert_twine.py --title 'Another Day at the MIA' --subtitle '' --author "Jerry Belich" --pubdate "2013-08-31-0500" --credits "" --lang "eng" --ver "1.0.0" --contact "Follow me: @j3rrytron" --linear --output ./story_linear --source ./another_day_at_the_mia_SRC.txt
```

## Generating a Choosatron Binary
Run all examples from a command line inside the folder containing the python scripts. _StoryTests_ is a folder one level deeper and the examples use that folder for test content.
```
./cdam_convert_twine.py --title 'Another Day at the MIA' --subtitle '' --author "Jerry Belich" --pubdate "2013-08-31-0500" --credits "" --lang "eng" --ver "1.0.0" --contact "Follow me: @j3rrytron" --binary --output ./story_bins --source ./another_day_at_the_mia_SRC.txt
```

**_If you have a title, name, or text that requires either single or double quotes, simply use the opposite quotes to contain the entire string._**

## Explanation of the Options
Not all options are shown above. Here are details on all available options. Text can be enclosed in single 'text' or double "text" quotes.

Option | Default | Max Length | Description
------ | ------- | ---------- | -----------
--title | "Untitled" | 64 | Title of your story.
--subtitle | "" | 32 | Addition to the title on a new line.
--author | "Anonymous" | 64 | The name of the writer.
--pubdate | 'YYYY-MM-DD-zzzz' | n/a | The '-zzzz' can start with + or - and then four digits zzzz, for timezone adjustment hours.
--credits | "" | 80 | Printed after play, place for additional credits or thanks.
--lang | "eng" | 3 | Three character language code (eng = american english).
--ver | "1.0.0" | 255.255.255 | A set of three integers for a story version number.
--contact | "Follow creator @j3rrytron online!" | 128 | Printed after play, a place to put contact info like a url or twitter.

Option | Description | Dependency
------ | ----------- | ----------
--source | Path to the Twine source file. | n/a
--output | Path to output folder. | n/a
--filename | Filename (appended with type, and proper extension). | n/a
--linear | Generates a playable linear document. | n/a
--randseed # | Allows regeneration with the same random output. | --linear
--binary | Generates a Choosatron compatible binary. | n/a
--html | BETA: Generates a playable HTML file. | n/a
--json | BROKEN: Generates a JSON file. | n/a

## Help!
If you get any errors, the first thing you should do is email the Twine source file to me (<name>.tws). Either you already know my email, tweet me at [@j3rrytron](https://www.twitter.com/j3rrytron), or you can use my contact form on [jerrytron.com](http://jerrytron.com). This script was never meant to be released, but here we are.
