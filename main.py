# Imports
import os
import json
import warnings

warnings.filterwarnings('ignore')

from cmd import Cmd
from PIL import Image

import SheetReader

# Constants
_RUNPATH_   = os.path.dirname(os.path.realpath(__file__))
_RESOURCES_ = os.path.join(_RUNPATH_, 'resources')


class Interactive(Cmd):
    prompt = '>'
    intro  = "Interactive shell for converting sheet music to tabs"

    def __init__(self):
        super(Interactive, self).__init__()
        self.instrument = None
        self.notes      = {}
        self.OOR_tab    = None
        self.sheet      = None
        self.song       = None
        self.tab_width  = 800
        self.beat_sep   = Image.open(os.path.join(_RESOURCES_, 'beat_sep.png'))
        self.beat_line  = Image.open(os.path.join(_RESOURCES_, 'beat_line.png'))


    def _get_img_for_note(self, note):
        img = self.notes.get(note)
        if img: return img
        return self.OOR_tab

    # Basic commands
    def default(self, vars):
        if vars.lower() in ['q', 'x', 'bye', 'stop']:
            return self.do_exit(vars)


    def do_exit(self, vars):
        '''Exit the interactive shell'''
        return True


    do_EOF = do_exit

    # Status commands
    def do_print_status(self, vars):
        '''Show the currently loaded settings'''
        range = sorted(self.notes.keys(), key=lambda x: x[1]+x[0]+x[2:])
        if len(range) == 0:
            range = "No notes"
        else:
            range = range[0]+' - '+range[-1]
        print("Instrument: %s"% self.instrument)
        print("Note range: %s"% range)
        print("Sheet file: %s"% self.sheet)


    def do_set_instrument(self, vars):
        '''Set instrument for tabs'''
        if not vars:
            print("Usage: set_instrument <instrument>"); return
        self.instrument = vars.lower()
        self.notes = {}
        for img in  os.listdir(_RESOURCES_):
            if not img.startswith(self.instrument):
                continue
            name = img.split('-', 1)[1].split('.')[0]
            if name == 'out-of-range':
                self.OOR_tab = Image.open(os.path.join(_RESOURCES_, img))
            else:
                name = name.replace('-sharp', '#')
                name = name[1]+name[0]+name[2:] # Swap octave note order
                self.notes[name] = Image.open(os.path.join(_RESOURCES_, img))
        if self.OOR_tab == None:
            print("WARNING: Instrument has no out-of-range tab")
            print(" -> Instrument not loaded")
            self.notes = {}
            self.instrument = None
            return
        if self.notes == {}:
            print("WARNING: No notes found for instrument %s"%vars)



    def do_set_sheet_width(self, vars):
        '''Set width of the tab sheet'''
        try:
            width = int(vars)
        except:
            print("Usage: set_sheet_width <width in pixels>"); return
        self.tab_width = width



    def do_load_sheet(self, vars):
        '''Load sheet music and translate it to notes'''
        self.song  = SheetReader.read_sheet(vars)
        self.song  = [[note.note for note in notes] for notes in self.song]
        self.sheet = vars



    def do_write_song_notes(self, vars):
        '''Write song notes to a flat file for later use (debug option)'''
        if not vars:
            print("Usage: write_song_notes <file>"); return
        if self.song == None:
            print("No song loaded"); return
        open(vars,'w').write(json.dumps(self.song, indent=2))



    def do_read_song_notes(self, vars):
        '''Read song notes from a flat file generated before (debug option)'''
        if not vars:
            print("Usage: read_song_notes <file>"); return
        self.song = json.loads(open(vars, 'r').read())



    def do_write_tabs(self, vars):
        '''Write song to tabs'''
        if not vars:
            print("Usage: write_tabs <file>"); return
        if not self.instrument:
            print("No instrument set"); return
        if self.notes == {}:
            print("No notes found for instrument"); return
        if self.song == None:
            print("No song loaded"); return

        tabs = [[self._get_img_for_note(n) for n in notes] for notes in self.song]
        tab_line_imgs = []

        bgcolor = (255, 255, 255)

        for block in tabs:
            widths, heights = zip(*(t.size for t in block))
            sum_widths = sum(widths)+self.beat_sep.width
            max_height = max(heights)+self.beat_line.height

            # Put all tabs on one line ending with beat sep
            tab_line = Image.new('RGB', (sum_widths, max_height), color=bgcolor)
            offset = 0
            for img in block:
                tab_line.paste(img, (offset, 0))
                offset += img.width
            tab_line.paste(self.beat_sep, (offset, 0))
            # Add beat line below
            beat_line = Image.new('RGB', (sum_widths-self.beat_sep.width, self.beat_line.height), color=bgcolor)
            offset = 0
            while offset < beat_line.width:
                beat_line.paste(self.beat_line, (offset, 0))
                offset += self.beat_line.width
            # Combine the two
            tab_line.paste(beat_line, (0, max_height-self.beat_line.height))
            # Add to tab lines
            tab_line_imgs.append(tab_line)

        # Generate final result
        widths, heights = zip(*(t.size for t in tab_line_imgs))
        tab_width = self.tab_width
        if max(widths) > tab_width:
            tab_width = max(widths) # Make wider if necessary
        tab_line_height = max(heights)

        result_height = tab_line_height
        result = Image.new('RGB', (tab_width, result_height), color=bgcolor)
        x_offset = 0
        y_offset = 0
        for i, img in enumerate(tab_line_imgs):
              if img.width+x_offset <= tab_width: # Append
                  result.paste(img, (x_offset, y_offset))
                  x_offset += img.width
              else: # New line -> expand picture
                  result_height += tab_line_height
                  result_bak     = Image.new('RGB', (tab_width, result_height), color=bgcolor)
                  result_bak.paste(result, (0, 0))
                  y_offset      += tab_line_height
                  result_bak.paste(img, (0, y_offset))
                  x_offset       = img.width
                  result = result_bak
              # result.save(str(i)+'.png') # Debug option
        result.save(vars)

Interactive().cmdloop()
