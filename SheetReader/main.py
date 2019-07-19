# Set to True to have visual output of note identification
_DEBUG_ = False

# Imports
import cv2
import numpy      as np
import os
import subprocess
import sys
import time
from midiutil.MidiFile3    import MIDIFile
from random                import randint
from SheetReader.best_fit  import fit
from SheetReader.note      import Note
from SheetReader.rectangle import Rectangle

_runpath = os.path.dirname(os.path.realpath(__file__))

# Lambda helper functions
cread = lambda f: cv2.imread(os.path.join(_runpath,'resources',f), 0)

# Constants
_VERBOSE_ = False

# Global vars
staff_imgs   = [cread(f) for f in ["staff2.png",      "staff.png"]]
quarter_imgs = [cread(f) for f in ["quarter.png",     "solid-note.png"]]
sharp_imgs   = [cread(f) for f in ["sharp.png"]]
flat_imgs    = [cread(f) for f in ["flat-line.png",   "flat-space.png"]]
half_imgs    = [cread(f) for f in ["half-space.png",  "half-note-line.png",
                                   "half-line.png",   "half-note-space.png"]]
whole_imgs   = [cread(f) for f in ["whole-space.png", "whole-note-line.png",
                                   "whole-line.png",  "whole-note-space.png"]]

staff_lower,   staff_upper,   staff_thresh   = 50, 150, 0.77
sharp_lower,   sharp_upper,   sharp_thresh   = 50, 150, 0.70
flat_lower,    flat_upper,    flat_thresh    = 50, 150, 0.77
quarter_lower, quarter_upper, quarter_thresh = 50, 150, 0.70
half_lower,    half_upper  ,  half_thresh    = 50, 150, 0.70
whole_lower,   whole_upper,   whole_thresh   = 50, 150, 0.70

# Functions
def write_and_show(name, data):
    cv2.imwrite(name, data)
    cmd = {'linux':'eog', 'win32':'explorer', 'darwin':'open'}[sys.platform]
    subprocess.run([cmd, name])


def debug_print(text):
    if not _DEBUG_:
        return
    print(text)


def to_img(matches, name, orig):
    if not _DEBUG_:
        return
    img = orig.copy()
    for r in matches:
        r.draw(img, (0, 0, 255), 2)
    write_and_show(name, img)


def locate_images(img, templates, start, stop, threshold):
    locations, scale = fit(img, templates, start, stop, threshold)
    img_locations = []
    for i in range(len(templates)):
        w, h = templates[i].shape[::-1]
        w *= scale
        h *= scale
        img_locations.append([Rectangle(pt[0], pt[1], w, h) for pt in zip(*locations[i][::-1])])
    return img_locations


def merge_recs(recs, threshold):
    filtered_recs = []
    while len(recs) > 0:
        r = recs.pop(0)
        recs.sort(key=lambda rec: rec.distance(r))
        merged = True
        while(merged):
            merged = False
            i = 0
            for _ in range(len(recs)):
                if r.overlap(recs[i]) > threshold or recs[i].overlap(r) > threshold:
                    r = r.merge(recs.pop(i))
                    merged = True
                elif recs[i].distance(r) > r.w/2 + recs[i].w/2:
                    break
                else:
                    i += 1
        filtered_recs.append(r)
    return filtered_recs


def read_sheet(path):
    img = cv2.imread(path, 0)
    img_gray = img#cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.cvtColor(img_gray,cv2.COLOR_GRAY2RGB)
    ret,img_gray = cv2.threshold(img_gray,127,255,cv2.THRESH_BINARY)
    img_width, img_height = img_gray.shape[::-1]

    debug_print("Matching staff image...")
    staff_recs = locate_images(img_gray, staff_imgs, staff_lower, staff_upper, staff_thresh)

    debug_print("Filtering weak staff matches...")
    staff_recs = [j for i in staff_recs for j in i]
    heights = [r.y for r in staff_recs] + [0]
    histo = [heights.count(i) for i in range(0, max(heights) + 1)]
    avg = np.mean(list(set(histo)))
    staff_recs = [r for r in staff_recs if histo[r.y] > avg]

    debug_print("Merging staff image results...")
    staff_recs = merge_recs(staff_recs, 0.01)
    to_img(staff_recs, "staff_recs_img.png", img)

    debug_print("Discovering staff locations...")
    staff_boxes = merge_recs([Rectangle(0, r.y, img_width, r.h) for r in staff_recs], 0.01)
    to_img(staff_boxes, "staff_boxes_img.png", img)

    debug_print("Matching sharp image...")
    sharp_recs = locate_images(img_gray, sharp_imgs, sharp_lower, sharp_upper, sharp_thresh)

    debug_print("Merging sharp image results...")
    sharp_recs = merge_recs([j for i in sharp_recs for j in i], 0.5)
    to_img(sharp_recs, "sharp_recs_img.png", img)

    debug_print("Matching flat image...")
    flat_recs = locate_images(img_gray, flat_imgs, flat_lower, flat_upper, flat_thresh)

    debug_print("Merging flat image results...")
    flat_recs = merge_recs([j for i in flat_recs for j in i], 0.5)
    to_img(flat_recs, "flat_recs_img.png", img)

    debug_print("Matching quarter image...")
    quarter_recs = locate_images(img_gray, quarter_imgs, quarter_lower, quarter_upper, quarter_thresh)

    debug_print("Merging quarter image results...")
    quarter_recs = merge_recs([j for i in quarter_recs for j in i], 0.5)
    to_img(quarter_recs, "quarter_recs_img.png", img)

    debug_print("Matching half image...")
    half_recs = locate_images(img_gray, half_imgs, half_lower, half_upper, half_thresh)

    debug_print("Merging half image results...")
    half_recs = merge_recs([j for i in half_recs for j in i], 0.5)
    to_img(half_recs, "half_recs_img.png", img)

    debug_print("Matching whole image...")
    whole_recs = locate_images(img_gray, whole_imgs, whole_lower, whole_upper, whole_thresh)

    debug_print("Merging whole image results...")
    whole_recs = merge_recs([j for i in whole_recs for j in i], 0.5)
    to_img(whole_recs, "whole_recs_img.png", img)

    note_groups = []
    for box in staff_boxes:
        staff_sharps = [Note(r, "sharp", box)
            for r in sharp_recs if abs(r.middle[1] - box.middle[1]) < box.h*5.0/8.0]
        staff_flats = [Note(r, "flat", box)
            for r in flat_recs if abs(r.middle[1] - box.middle[1]) < box.h*5.0/8.0]
        quarter_notes = [Note(r, "4,8", box, staff_sharps, staff_flats)
            for r in quarter_recs if abs(r.middle[1] - box.middle[1]) < box.h*5.0/8.0]
        half_notes = [Note(r, "2", box, staff_sharps, staff_flats)
            for r in half_recs if abs(r.middle[1] - box.middle[1]) < box.h*5.0/8.0]
        whole_notes = [Note(r, "1", box, staff_sharps, staff_flats)
            for r in whole_recs if abs(r.middle[1] - box.middle[1]) < box.h*5.0/8.0]
        staff_notes = quarter_notes + half_notes + whole_notes
        staff_notes.sort(key=lambda n: n.rec.x)
        staffs = [r for r in staff_recs if r.overlap(box) > 0]
        staffs.sort(key=lambda r: r.x)
        note_color = (randint(0, 255), randint(0, 255), randint(0, 255))
        note_group = []
        i = 0; j = 0;
        while(i < len(staff_notes)):
            if (staff_notes[i].rec.x > staffs[j].x and j < len(staffs)):
                r = staffs[j]
                j += 1;
                if len(note_group) > 0:
                    note_groups.append(note_group)
                    note_group = []
                note_color = (randint(0, 255), randint(0, 255), randint(0, 255))
            else:
                note_group.append(staff_notes[i])
                staff_notes[i].rec.draw(img, note_color, 2)
                i += 1
        note_groups.append(note_group)

    if _VERBOSE_:
        for r in staff_boxes:
            r.draw(img, (0, 0, 255), 2)
        for r in sharp_recs:
            r.draw(img, (0, 0, 255), 2)
        flat_recs_img = img.copy()
        for r in flat_recs:
            r.draw(img, (0, 0, 255), 2)

        write_and_show('res.png', img)

    for note_group in note_groups:
        print([ note.note + " " + note.sym for note in note_group])
    return note_groups


def create_midi(note_groups):
    midi = MIDIFile(1)

    track = 0
    time = 0
    channel = 0
    volume = 100

    midi.addTrackName(track, time, "Track")
    midi.addTempo(track, time, 140)

    for note_group in note_groups:
        duration = None
        for note in note_group:
            note_type = note.sym
            if note_type == "1":
                duration = 4
            elif note_type == "2":
                duration = 2
            elif note_type == "4,8":
                duration = 1 if len(note_group) == 1 else 0.5
            pitch = note.pitch
            midi.addNote(track,channel,pitch,time,duration,volume)
            time += duration

    #midi.addNote(track,channel,pitch,time,4,0)
    # And write it to disk.
    binfile = open("output.mid", 'wb')
    midi.writeFile(binfile)
    binfile.close()


if __name__ == "__main__":
    img_file = sys.argv[1:][0]
    notes    = read_sheet(img_file)
    create_midi(notes)
