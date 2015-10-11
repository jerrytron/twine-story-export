# twine-story-export
A repo for code that will import Twine source and export content in other formats.

Download and install Twine:
OSX: http://twinery.org/downloads/twine_1.4.2_osx.zip
Win: http://twinery.org/downloads/twine_1.4.2_win.exe

Note: I've never tried ANY of this on Windows...

Here is an example using one of my stories. I've included the original Twine file and the source file exported. To export, open a Twine story and go to File -> Export -> Twee Source Code
Save it as a .txt file. This is the source file you feed the script.

./cdam_convert_twine.py --title "Another Day at the MIA" --author "Jerry Belich" --ver "1.0.0" --contact "@j3rrytron" --source ./another_day_at_the_mia_SRC.txt --output ./ --linear

If you include --contact, that is text that will print out at the END of the story. Title and author print out at the beginning.

Output is the path you want to create the file, above it just creates it where you execute the script. Source is simply the path to the src file Twine generates. Remember, you don't run this on the Twine file directly!