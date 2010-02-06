#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
#
# Application Identifier: goo-gly@appspot.com
#                         goo-gly+insert@appspot.com
#                         goo-gly+textreplace@appspot.com
#                         goo-gly+linkreplace@appspot.com
#                         goo-gly+replace@appspot.com
#
################################################################################
#
# Goo-gly
#
# The MIT License
#
# Copyright (c) 2010 Jaken. (Shoji Morimoto, Jaken.Jarvis@gmail.com)
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
import sys

################################################################################
# Module header and authors
################################################################################
"""Goo-gly URL Shortener using goo.gl(Google URL Shortener)
"""
__license__ = "MIT License"
__authors__ = [
  '"Jaken" <Jaken.Jarvis@gmail.com>',
]

__appname__ = "Goo-gly URL Shortener using goo.gl(Google URL Shortener)"
__version__ = "2.0.2"
__profile_url__ = "http://code.google.com/p/goo-gly/"
__image_url__ = "http://goo-gly.appspot.com/assets/Goo-gly_icon.png"

__pychecker__ = '' #'no-callinit no-classattr'


################################################################################
# Global variable
################################################################################
param_all         = 1
param_select      = 2
param_insert      = 16
param_textreplace = 32
param_linkreplace = 64
param_replace     = 128

################################################################################
# Events handler
################################################################################
def OnWaveletSelfAdded(properties, context):
    """ Robot自身がWaveに参加した時の処理 """
    logging.info("OnWaveletSelfAdded()")

    if "proxyingFor" in context.extradata:
        proxyingFor = context.extradata['proxyingFor'].lower()
    else:
        proxyingFor = ""
    logging.debug("  proxyingFor: %s" % proxyingFor)

    # Judg mode
    param = JudgMode(proxyingFor)
    if not IsMode(param, param_all):
        # All未指定の場合はツールバークリック
        # Blipを全てチェックする
        for blip in context.GetBlips():
            mode = 0
            googlylinkflg = False
            for note in blip.GetAnnotations():
                if "goo-gly.appspot.com/link" in note.name:
                    googlylinkflg = True
                    mode = JudgMode(note.value)
            if googlylinkflg:
                editSelectToolbar(blip, mode)


def OnDocumentChanged(properties, context):
    """ 文書内容変更時の処理 """
    logging.info("OnDocumentChanged()")

    if "proxyingFor" in context.extradata:
        proxyingFor = context.extradata['proxyingFor'].lower()
    else:
        proxyingFor = ""
    logging.debug("  proxyingFor: %s" % proxyingFor)

    blip = context.GetBlipById(properties['blipId'])

    # Judg mode
    param = JudgMode(proxyingFor)
    if not IsMode(param, param_all):
        # All未指定の場合はツールバークリック
        mode = 0
        googlylinkflg = False
        for note in blip.GetAnnotations():
            if "goo-gly.appspot.com/link" in note.name:
                googlylinkflg = True
                mode = JudgMode(note.value)
        if googlylinkflg:
            editSelectToolbar(blip, mode)


def OnBlipSubmitted(properties, context):
    """ Blipの送信（Done）時の処理 """
    logging.info("OnBlipSubmitted()")

    if "proxyingFor" in context.extradata:
        proxyingFor = context.extradata['proxyingFor'].lower()
    else:
        proxyingFor = ""
    logging.debug("  proxyingFor: %s" % proxyingFor)

    blip = context.GetBlipById(properties['blipId'])

    # Judg mode
    param = JudgMode(proxyingFor)
    if IsMode(param, param_all):
        editBlipDone(blip, param)
    elif IsMode(param, param_insert | param_textreplace | param_linkreplace | param_replace):
        editBlipDone(blip, param)
    elif not IsMode(param, param_all):
        # All未指定の場合はツールバークリック
        mode = 0
        googlylinkflg = False
        for note in blip.GetAnnotations():
            if "goo-gly.appspot.com/link" in note.name:
                googlylinkflg = True
                mode = JudgMode(note.value)
        if googlylinkflg:
            editSelectToolbar(blip, mode)


################################################################################
# Function
################################################################################
def editSelectToolbar(blip, mode):
    """ ToolbarでAnnotationをつけた場合の処理 """
    logging.debug(u"editSelectToolbar")

    doc = blip.GetDocument()
    elems = blip.GetElements()

    # Action Annotation.
    addGooglyLinkList = []
    for note in blip.GetAnnotations():
        if "goo-gly.appspot.com/link" in note.name:
            logging.debug(u"Annotation goo-gly.appspot.com/link : %s" % (note.value))

            addGooglyLinkList.append((note))
            logging.debug(u"addGooglyLinkList : %s" % (note))

    addLinkList = []
    for glinknote in addGooglyLinkList:
        doc.DeleteAnnotationsInRange(glinknote.range, "goo-gly.appspot.com/link")

        for note in blip.GetAnnotations():
            if IsExecute(note.name, note.value):
                # check range
                if IsSelectRange(glinknote.range, note.range):
                    linktext = doc.GetText()[note.range.start: note.range.end]
                    pack = {
                        'text': linktext,
                        'name': note.name,
                        'value': note.value,
                        'start': note.range.start,
                        'end': note.range.end
                        }
                    addLinkList.append((pack))

    editShortenUrl(blip, addLinkList, mode)



def editBlipDone(blip, mode):
    """ Blip編集後にDoneを押下した場合の処理 """
    logging.debug(u"editBlipDone")

    doc = blip.GetDocument()
    elems = blip.GetElements()

    addLinkList = []
    for note in blip.GetAnnotations():
        if IsExecute(note.name, note.value):
            linktext = doc.GetText()[note.range.start: note.range.end]
            pack = {
                'text': linktext,
                'name': note.name,
                'value': note.value,
                'start': note.range.start,
                'end': note.range.end
                }
            addLinkList.append((pack))

    editShortenUrl(blip, addLinkList, mode)


def editShortenUrl(blip, addLinkList, mode):
    """ ShortenUrlの編集処理 """
    logging.debug(u"editShortenUrl mode: %s" % (mode))

    doc = blip.GetDocument()
    elems = blip.GetElements()

    gapcount = 0
    for packobject in addLinkList:
        logging.debug(u"packobject: %s" % (packobject))

        gapnoterange = document.Range(packobject['start'] + gapcount, packobject['end'] + gapcount)

        bfTextLength = len(packobject['text'])
        afTextLength = len(packobject['text'])

        longurl = packobject['value']
        shorturl = get_short_url(longurl, None)

        if len(shorturl) == 0:
            continue

        if IsMode(mode, param_insert):
            ##################################################
            logging.debug(u"**** mode: %s" % (mode))

            rangeText  = document.Range(gapnoterange.start  , gapnoterange.end + 1 + len(shorturl))
            rangeSpace = document.Range(gapnoterange.end    , gapnoterange.end + 1)
            rangeLink  = document.Range(gapnoterange.end + 1, gapnoterange.end + 1 + len(shorturl))

            tolerance = 5 # 許容範囲
            nextlinktext = doc.GetText()[gapnoterange.end: gapnoterange.end + 1 + len(shorturl) + tolerance]
            if shorturl in nextlinktext:
                logging.debug(u"find shorter link")

                # 消える場合があるのでリンク張りなおしする。
                doc.DeleteAnnotationsInRange(rangeText, "link/auto")
                doc.DeleteAnnotationsInRange(rangeText, "link/manual")

                doc.SetAnnotation(gapnoterange, packobject['name'], packobject['value'])
                doc.SetAnnotation(rangeLink, 'link/manual', shorturl)

            else:
                logging.debug(u"insert shorter link: %s" % (shorturl))

                text = u"%s %s" % (packobject['text'], shorturl)
                doc.SetTextInRange(gapnoterange, text)

                # 消える場合があるのでリンク張りなおしする。
                doc.DeleteAnnotationsInRange(rangeText, "link/auto")
                doc.DeleteAnnotationsInRange(rangeText, "link/manual")

                doc.SetAnnotation(gapnoterange, packobject['name'], packobject['value'])
                doc.SetAnnotation(rangeLink, 'link/manual', shorturl)

                afTextLength = len(text)

                #doc.InsertText(rangeSpace.start, " ")
                #doc.DeleteAnnotationsInRange(rangeSpace, packobject['name'])
                #doc.InsertText(rangeLink.start, "%s" % (shorturl))
                #doc.SetAnnotation(rangeLink, 'link/manual', shorturl)

                #afTextLength += 1 + len(shorturl)

        elif IsMode(mode, param_textreplace):
            ##################################################
            logging.debug(u"**** mode: %s" % (mode))

            rangeLink  = document.Range(gapnoterange.start, gapnoterange.start + len(shorturl))
            doc.SetTextInRange(gapnoterange, shorturl)
            doc.SetAnnotation(rangeLink, 'link/manual', longurl)

            afTextLength = len(shorturl)

        elif IsMode(mode, param_linkreplace):
            ##################################################
            logging.debug(u"**** mode: %s" % (mode))

            doc.DeleteAnnotationsInRange(gapnoterange, packobject['name'])
            doc.SetAnnotation(gapnoterange, 'link/manual', shorturl)

        elif IsMode(mode, param_replace):
            ##################################################
            logging.debug(u"**** mode: %s" % (mode))

            #rangeLink  = document.Range(gapnoterange.start, gapnoterange.start + len(shorturl))
            doc.SetTextInRange(gapnoterange, shorturl)
            #doc.SetAnnotation(rangeLink, 'link/auto', shorturl)

            afTextLength = len(shorturl)


        gapcount += (afTextLength - bfTextLength)


def JudgMode(target):
    """ Mode判定処理 """
    ret = 0
    if "all" in target:
        ret = ret | param_all
    if "select" in target:
        ret = ret | param_select
    if "insert" in target:
        ret = ret | param_insert
    if "textreplace" in target:
        ret = ret | param_textreplace
    if "linkreplace" in target:
        ret = ret | param_linkreplace
    if "replace" in target:
        ret = ret | param_replace
    return ret

def IsMode(mode, target):
    """ Mode比較処理 """
    return ((mode & target) != 0)


def IsSelectRange(range, target):
    """ 選択範囲に重なっているか判定する処理 """
    ret = False
    if (target.start <= range.start) and (target.end >= range.end):
        ret = True
    if (target.start >= range.start) and (target.start < range.end):
        ret = True
    if (target.end >= range.start) and (target.end <= range.end):
        ret = True
    return ret


def IsExecute(notename, notelink):
    """ ShortenURLの実行対象か判定する処理 """
    ret = False
    if "link" in notename:
        if notelink.startswith("http://goo.gl/"):
            ret = False
        else:
            if "link/auto" in notename:
                ret = True
            elif "link/manual" in notename:
                ret = True
            elif "link/wave" in notename:
                ret = False
            elif "goo-gly.appspot.com/link" in notename:
                ret = False
            else:
                ret = False
    return ret



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
    try:
        short_url = simplejson.loads(res.read())['short_url']
        logging.debug(u"Shorter\n L-URL: %s\n S-URL: %s" % (uri, short_url))
    except:
        short_url = ""
        logging.warning(u"Shorter\n L-URL: %s\n S-URL: Exception: %s" % (uri, sys.exc_info()[0]))
    return short_url


################################################################################
# Main
################################################################################
if __name__ == '__main__':
    myRobot = robot.Robot(__appname__, image_url=__image_url__, version=__version__, profile_url=__profile_url__)
    myRobot.RegisterHandler(events.WAVELET_SELF_ADDED, OnWaveletSelfAdded)
    myRobot.RegisterHandler(events.DOCUMENT_CHANGED, OnDocumentChanged)
    myRobot.RegisterHandler(events.BLIP_SUBMITTED, OnBlipSubmitted)
    myRobot.Run()

