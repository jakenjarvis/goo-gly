#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
#
# Application Identifier: goo-gly@appspot.com
#
################################################################################
#
# goo-gly
#
# The MIT License
#
# Copyright (c) 2010 Jaken.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
################################################################################
# Module header and authors
#
"""Shorten URL with goo.gl
"""
__license__ = "MIT License"
__authors__ = [
  '"Jaken" <Jaken.Jarvis@gmail.com>',
]
__version__ = "1.0.0"
__pychecker__ = '' #'no-callinit no-classattr'

################################################################################
# Imports
################################################################################
from waveapi import events
from waveapi import model
from waveapi import robot
from waveapi import document

from django.utils import simplejson

import urllib
import logging

################################################################################
# Global variable
################################################################################



################################################################################
# Events handler
################################################################################
def OnBlipSubmitted(properties, context):
    """ Blipの送信（Done）時の処理 """
    logging.info("OnBlipSubmitted()")
    blip = context.GetBlipById(properties['blipId'])
    editBlip(blip)

################################################################################
# Function
################################################################################
def editBlip(blip):
    """ Blipを編集しショートURLを挿入する """
    doc = blip.GetDocument()
    elems = blip.GetElements()

    addLinkList = []

    for note in blip.GetAnnotations():
        linktext = doc.GetText()[note.range.start: note.range.end]

        #logging.debug(u"Annotation\n  Text: %s\n  Name: %s\n  Value: %s\n  Start: %s\n  End: %s\n" % (
        #                linktext,
        #                note.name,
        #                note.value,
        #                note.range.start,
        #                note.range.end)
        #                )

        replaceflg = False

        if "link" in note.name:
            if note.value.startswith("http://goo.gl/"):
                # not replace
                replaceflg = False
            else:
                if "link/auto" in note.name:
                    # replace
                    replaceflg = True
                elif "link/manual" in note.name:
                    # replace
                    replaceflg = True
                else:  #"link/wave"
                    # not replace
                    replaceflg = False

        if replaceflg:
            pack = {
                'text': linktext,
                'name': note.name,
                'value': note.value,
                'start': note.range.start,
                'end': note.range.end
                }
            addLinkList.append((pack))

            logging.debug(u"pack: %s" % (pack))
        #else:
        #    logging.debug(u"shorter non replace")


    logging.debug(u"**** Insert Shorten URL ****")
    gapcount = 0
    for packobject in addLinkList:
        gapnoterange = document.Range(gapcount + packobject['start'], gapcount + packobject['end'])

        # for debug
        #linktext = doc.GetText()[gapnoterange.start: gapnoterange.end]
        #logging.debug(u"Gapcheck:\n%s\n%s" % (packobject['text'], linktext))

        longurl = packobject['value']
        shorturl = get_short_url(longurl, None)
        #logging.debug(u"Shorter\n L-URL: %s\n S-URL: %s" % (
        #                longurl,
        #                shorturl)
        #                )

        # ここではまだSPACEを入れてない
        tolerance = 5
        nextlinktext = doc.GetText()[gapnoterange.end: gapnoterange.end + 1 + len(shorturl) + tolerance]
        #logging.debug(u"FindString\n S-URL: %s\n V-TXT: %s" % (
        #                shorturl,
        #                nextlinktext)
        #                )

        if shorturl in nextlinktext:
            logging.debug(u"find shorter link")
        else:
            logging.debug(u"insert shorter link: %s" % (shorturl))

            rangeSpace = document.Range(gapnoterange.end    , gapnoterange.end + 1)
            rangeLink  = document.Range(gapnoterange.end + 1, gapnoterange.end + 2 + len(shorturl))

            #logging.debug(u"Range\ngapcount: %s\n GAP: %s\n SPC: %s\n LNK: %s" % (
            #                gapcount,
            #                gapnoterange,
            #                rangeSpace,
            #                rangeLink)
            #                )

            # It doesn't work!
            doc.InsertText(rangeSpace.start, " ")
            doc.DeleteAnnotationsInRange(rangeSpace, packobject['name'])

            doc.InsertText(rangeLink.start, "%s" % (shorturl))
            #doc.SetAnnotation(rangeLink, 'link/auto', shorturl)
            doc.SetAnnotation(rangeLink, 'link/manual', shorturl)

            gapcount += 1 + len(shorturl)


################################################################################
# goo.gl URL Shortener PythonAPI [Thanks LaclefYoshi]
# http://d.hatena.ne.jp/LaclefYoshi/20091216/1260891200
################################################################################
def _c(vals):
    l = 0
    for val in vals:
        l += val & 4294967295
    return l

def _d(l):
    if l <=  0:
        l += 4294967296
    m = str(l)
    o = 0
    n = False
    for char in m[::-1]:
        q = int(char)
        if n:
            q *= 2
            o += q / 10 + q % 10  # JSだと Math.floor(q / 10) + q % 10
        else:
            o += q
        n = not(n)
    m = o % 10
    o = 0
    if m != 0:
        o = 10 - m
        if len(str(l)) % 2 == 1:
            if o % 2 == 1:
                o += 9
            o /= 2
    return str(o) + str(l)

def _e(uri):
    m = 5381
    for char in uri:
        # m = _c([m << 5, m, struct.unpack("B", char)[0]])
        m = _c([m << 5, m, ord(char)])
    return m

def _f(uri):
    m = 0
    for char in uri:
        # m = _c([struct.unpack("B", char)[0], m << 6, m << 16, -1 * m])
        m = _c([ord(char), m << 6, m << 16, -1 * m])
    return m

def _make_auth_token(uri):
    i = _e(uri)
    i = i >> 2 & 1073741823
    i = i >> 4 & 67108800 | i & 63
    i = i >> 4 & 4193280 | i & 1023
    i = i >> 4 & 245760 | i & 16383
    h = _f(uri)
    k = (i >> 2 & 15) << 4 | h & 15
    k |= (i >> 6 & 15) << 12 | (h >> 8 & 15) << 8
    k |= (i >> 10 & 15) << 20 | (h >> 16 & 15) << 16
    k |= (i >> 14 & 15) << 28 | (h >> 24 & 15) << 24
    j = "7" + _d(k)
    return j

def get_short_url(uri, user):
    if user is None:
        user = 'toolbar@google.com'
    token = _make_auth_token(uri)
    opt = 'user='+user+'&'+urllib.urlencode({'url':uri})+'&auth_token='+token
    # print opt
    ggl_url = 'http://goo.gl/api/url'
    res = urllib.urlopen(ggl_url, opt)
    # print res.read()
    short_url =  simplejson.loads(res.read())['short_url']
    return short_url


################################################################################
# Main
################################################################################
if __name__ == '__main__':
    myRobot = robot.Robot('goo-gly goo.gl(Google URL Shortener)',
        image_url='http://goo-gly.appspot.com/assets/Goo-gly_icon.png',
        version='1',
        profile_url='http://goo-gly.appspot.com/')
    myRobot.RegisterHandler(events.BLIP_SUBMITTED, OnBlipSubmitted)
    myRobot.Run()

