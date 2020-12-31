#!/usr/bin/python3

import sys

__VERSION__ = "2020.12.30"

__ABOUT__  = "= NAS directory browser in Json format = version %s =" % (__VERSION__)

__USAGE__  = """
%(about)s

usage: %(exe)s NasRoot RelDir PageNum PageSize

NasRoot  ... NAS root directory
RelDir   ... relative dir to NAS root dir
PageNum  ... page to display
PageSize ... page size
""" % { 'about': __ABOUT__, 'exe': sys.argv[0] }

VERBOSE = 0

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

    def get_full_path(self, relpath):
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

    def get_dir_page(self, relpath, pagenum, sortfnc, pagesize):
        """ list directory entries for page pagenum and pagesize """
        #full = [ d for d in os.scandir(os.path.join(self.root, path)) if d.is_dir() or self.is_media_file(d.name) ]
        full = []
        with os.scandir(self.get_full_path(relpath)) as sd:
            for e in sd:
                if self.show_in_list(e):
                    full.append(e)
        msg(5, 'DBG5: full-unsorted-list: %s' % full)
        # sort and splice
        page = sorted(full, key=sortfnc)[pagenum:(pagenum+1)*pagesize]
        msg(4, 'DBG4: sorted-page: %s' % page)
        # format
        return [ self.dirFormat % e.name if e.is_dir() else e.name for e in page ]

    def get_dir_page_alpha(self, relpath, pagenum=0, pagesize=10):
        """ list dir entries alphabetically for pagenum and pagesize """
        return self.get_dir_page(relpath, pagenum, lambda entry: entry.name, pagesize)

    def get_dir_page_new(self, relpath, pagenum=0, pagesize=10):
        """ list dir entries by date added (the newest first) for pagenum and pagesize """
        now = time.time()
        return self.get_dir_page(relpath, pagenum, lambda entry: now - entry.stat().st_mtime, pagesize)


if __name__ == '__main__':

    usage()

    nasRoot  = sys.argv[1]
    relDir   = sys.argv[2]
    pageNum  = int(sys.argv[3])
    pageSize = int(sys.argv[4])

    msg(3, "DBG3: nasRoot(%s) relDir(%s) pageNum(%d) pageSize(%d)" % (nasRoot, relDir, pageNum, pageSize))

    ns = Nas(nasRoot)
    ls = ns.get_dir_page_new(relDir, pageNum, pageSize)

    msg(3, 'DBG3: ls: %s' %ls)

    print(json.dumps(ls))
