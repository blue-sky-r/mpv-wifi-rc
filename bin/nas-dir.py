#!/usr/bin/python3

import sys

__VERSION__ = "2020.01.16"

__ABOUT__  = "= NAS directory browser in Json format {id: string, title: string}= version %s =" % (__VERSION__)

__USAGE__  = """
%(about)s

usage: %(exe)s NasRoot RelDir IdxFrom IdxTo

NasRoot  ... NAS root directory
RelDir   ... relative dir to NAS root dir
IdxFrom  ... index from
IdxTo    ... index to
""" % { 'about': __ABOUT__, 'exe': sys.argv[0] }

VERBOSE = 5

import os, json, time, re

def msg(level, txt):
    """ verbose output """
    if level > VERBOSE: return
    print(txt)

def usage(n=4):
    """" usage help """
    if len(sys.argv) > n: return
    print(__USAGE__)
    sys.exit(-1)


class Nas:
    """ NAS """

    mediaFiles = ['.avi', '.mp4', '.mkv', '.mpg', '.webm']
    dirFormat  = " > %s"

    def __init__(self, root):
        """ NAs root dir """
        self.root = root
        self.nas = 'NAS:'

    def is_nas_mounted():
        """ check if NAS dir is auto-mounted via autofs """
        r = false
        with os.scandir(self.root) as sd:
            for entry in sd:
                r = true
                break
        return r

    def is_media_file(self, fname):
        """ returns true is fname is ending with any of the mediaFiles extension """
        return any([ fname.endswith(ext) for ext in self.mediaFiles ])

    def show_in_list(self, entry):
        """ which entries to show in dir listing - subdirs + media files """
        return entry.is_dir() or self.is_media_file(entry.name)

    def get_full_pathx(self, relpath):
        """ combine NAS root and relpath (while removing dir format)"""
        # regex to match formatted dir entry
        regex = '(' + self.dirFormat % '(.+)' + ')'
        # regex to replace formatted part to unformatted part of rel path
        relpathunf = re.sub(regex, '\\2', relpath)
        msg(5, 'DBG5: re.sub(%s, %s, %s) -> "%s"' % (regex, '\\2', relpath, relpathunf))
        # combine root and unformatted rel path
        fullpath = os.path.join(self.root, relpathunf)
        msg(4, 'DBG4: get_full_path(%s) -> "%s"' %(relpath, fullpath))
        # result
        return fullpath

    def get_full_path(self, relpath):
        """ combine NAS root and relpath (while removing dir format)"""
        path = os.path.join(self.root, relpath)
        msg(4, 'DBG4: get_full_path(%s) -> "%s"' %(relpath, path))
        return path

    def format_item(self, entry):
        """ format/build item from entry / format directories """
        return {
            "id":    self.get_full_path(entry.name),
            "title": self.dirFormat % entry.name if entry.is_dir() else entry.name
        }

    def get_dir_fromto(self, relpath, idxfrom, idxto, sortfnc):
        """ list directory entries for index from..to """
        msg(5, 'DBG5: get_dir_fromto(relpath:%s, idxfrom:%d, idxto:%d)' % (relpath, idxfrom, idxto))
        #full = [ d for d in os.scandir(os.path.join(self.root, path)) if d.is_dir() or self.is_media_file(d.name) ]
        full = []
        with os.scandir(self.get_full_path(relpath)) as sd:
            for e in sd:
                if self.show_in_list(e):
                    full.append(e)
        msg(5, 'DBG5: full-unsorted-list: %s' % full)
        # sort and splice
        page = sorted(full, key=sortfnc)[idxfrom:idxto+1]
        msg(4, 'DBG4: sorted-page: %s' % page)
        # format
        return [ self.format_item(e) for e in page ]

    def get_dir_alpha(self, relpath, idxfrom, idxto):
        """ list dir entries alphabetically for idx range """
        return self.get_dir_fromto(relpath, idxfrom, idxto, lambda entry: entry.name)

    def get_dir_new(self, relpath, idxfrom, idxto):
        """ list dir entries by date added (the newest first) for idx range """
        now = time.time()
        return self.get_dir_fromto(relpath, idxfrom, idxto, lambda entry: now - entry.stat().st_mtime)


if __name__ == '__main__':

    usage()

    nasRoot  = sys.argv[1]
    relDir   = sys.argv[2]
    idxFrom  = int(sys.argv[3])
    idxTo    = int(sys.argv[4])

    msg(3, "DBG3: nasRoot(%s) relDir(%s) idxFrom(%d) idxTo(%d)" % (nasRoot, relDir, idxFrom, idxTo))

    ns = Nas(nasRoot)
    ls = ns.get_dir_alpha(relDir, idxFrom, idxTo)

    msg(3, 'DBG3: ls: %s' %ls)

    print(json.dumps(ls))
