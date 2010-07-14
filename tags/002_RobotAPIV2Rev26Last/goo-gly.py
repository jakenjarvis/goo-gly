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
import urllib
import urllib2
import logging
import sys
import uuid
import httplib
import base64

from waveapi import appengine_robot_runner
from waveapi import element
from waveapi import events
from waveapi import ops
from waveapi import robot

from django.utils import simplejson

################################################################################
# Module header and authors
################################################################################
"""Goo-gly URL Shortener using goo.gl(Google URL Shortener)
"""
__license__ = "MIT License"
__authors__ = [
  '"Jaken(Shoji Morimoto)" <Jaken.Jarvis@gmail.com>',
]

__appname__ = "Goo-gly URL Shortener using goo.gl(Google URL Shortener)"
__version__ = "3.0.0"
__profile_url__ = "http://code.google.com/p/goo-gly/"
__image_url__ = "http://goo-gly.appspot.com/assets/Goo-gly_icon.png"

__pychecker__ = '' #'no-callinit no-classattr'


################################################################################
# Global variable
################################################################################
param_all           = 0x0001 #and undef 0x0000
param_select        = 0x0002
param_insert        = 0x0010
param_textreplace   = 0x0020
param_linkreplace   = 0x0040
param_replace       = 0x0080

link_annotation     = "goo-gly.appspot.com/link"
keep_annotation     = "goo-gly.appspot.com/keep" #RobotAPIV1 array version(Abolition)
save_annotation     = "goo-gly.appspot.com/save" #RobotAPIV2 csv version

exectype_none       = 0x0000
exectype_revers     = 0x0001
exectype_link_ltos  = 0x0002
exectype_link_stol  = 0x0004

ShortenUrl_Services = [
    {'url': "http://goo.gl/", 'domain': "goo.gl", 'status': 301},
    {'url': "http://bit.ly/", 'domain': "bit.ly", 'status': 301}
]

################################################################################
# Events handler
################################################################################
def OnWaveletSelfAdded(event, wavelet):
    """ Robot自身がWaveに参加した時の処理 """
    logging.info(u"OnWaveletSelfAdded()")

    proxyingFor = GetProxyingFor(wavelet)

    # Judg mode
    param = JudgMode(proxyingFor)
    if not IsMode(param, param_all):
        # All未指定の場合はツールバークリック
        # Blipを全てチェックする
        for blipid in wavelet.blips:
            blip = wavelet.blips.get(blipid)
            logging.debug(u"blip %s : %s" % (blipid, blip))

            googlylinkflg = False
            for note in blip.annotations:
                logging.debug(u"Annotation %s : %s | %s = %s" % (note.start, note.end, note.name, note.value))
                if link_annotation in note.name:
                    googlylinkflg = True
            if googlylinkflg:
                editSelectToolbar(event, wavelet, blip)


def OnDocumentChanged(event, wavelet):
    """ 文書内容変更時の処理 """
    logging.info(u"OnDocumentChanged()")


def OnAnnotatedTextChanged(event, wavelet):
    """ アノテーションのテキスト変化時の処理 """
    logging.info(u"OnAnnotatedTextChanged()")

    proxyingFor = GetProxyingFor(wavelet)

    blip = event.blip

    # Judg mode
    param = JudgMode(proxyingFor)
    if not IsMode(param, param_all):
        # ツールバークリック
        googlylinkflg = False
        for note in blip.annotations:
            logging.debug(u"Annotation %s : %s | %s = %s" % (note.start, note.end, note.name, note.value))
            if link_annotation in note.name:
                googlylinkflg = True
        if googlylinkflg:
            editSelectToolbar(event, wavelet, blip)


def OnBlipSubmitted(event, wavelet):
    """ Blipの送信（Done）時の処理 """
    logging.info(u"OnBlipSubmitted()")

    proxyingFor = GetProxyingFor(wavelet)

    blip = event.blip

    # Judg mode
    param = JudgMode(proxyingFor)
    if IsMode(param, param_all):
        # All指定の場合はBlip全編集
        editBlipDone(event, wavelet, blip, param)

    elif IsMode(param, param_select):
        # Selectの場合はツールバークリック
        googlylinkflg = False
        for note in blip.annotations:
            logging.debug(u"Annotation %s : %s | %s = %s" % (note.start, note.end, note.name, note.value))
            if link_annotation in note.name:
                googlylinkflg = True
        if googlylinkflg:
            editSelectToolbar(event, wavelet, blip)

    elif IsMode(param, param_insert | param_textreplace | param_linkreplace | param_replace):
        # All未指定で４モード指定の場合はBlip全編集
        editBlipDone(event, wavelet, blip, param)

    else:
        # All未指定の場合はツールバークリック
        googlylinkflg = False
        for note in blip.annotations:
            logging.debug(u"Annotation %s : %s | %s = %s" % (note.start, note.end, note.name, note.value))
            if link_annotation in note.name:
                googlylinkflg = True
        if googlylinkflg:
            editSelectToolbar(event, wavelet, blip)

    #--------------------------------------------------
    # Delete link/auto Annotations
    #--------------------------------------------------
    lstAutoLinks = [pack for pack in blip.annotations if pack.name == "link/auto"]
    lstManualLinks = [pack for pack in blip.annotations if pack.name == "link/manual"]
    for packManual in lstManualLinks:
        for packAuto in lstAutoLinks:
            if (packAuto.start == packManual.start) and (packAuto.end == packManual.end):
                logging.debug(u"clear_annotation:auto %s : %s | %s = %s" % (packAuto.start, packAuto.end, packAuto.name, packAuto.value))
                blip.range(packAuto.start, packAuto.end).clear_annotation("link/auto") # auto


def OnOperationError(event, wavelet):
    """ OperationError時の処理 """
    logging.info(u"OnOperationError()")
    if isinstance(event, events.OperationError):
        logging.error(u"OperationError: id=%s, message: %s" % (event.operation_id, event.error_message))


################################################################################
# Function
################################################################################
def editSelectToolbar(event, wavelet, blip):
    """ ToolbarでAnnotationをつけた場合の処理 """
    logging.debug(u"editSelectToolbar")

    #--------------------------------------------------
    # Delete link/auto Annotations
    #--------------------------------------------------
    lstAutoLinks = [pack for pack in blip.annotations if pack.name == "link/auto"]
    lstManualLinks = [pack for pack in blip.annotations if pack.name == "link/manual"]
    for packManual in lstManualLinks:
        for packAuto in lstAutoLinks:
            if (packAuto.start == packManual.start) and (packAuto.end == packManual.end):
                logging.debug(u"clear_annotation:auto %s : %s | %s = %s" % (packAuto.start, packAuto.end, packAuto.name, packAuto.value))
                blip.range(packAuto.start, packAuto.end).clear_annotation("link/auto") # auto

    # Action Annotation.
    lstGooglyLinkAnnotations = []
    lstGooglySaveAnnotations = []
    for note in blip.annotations:
        if link_annotation in note.name:
            lstGooglyLinkAnnotations.append(note)
        if (save_annotation in note.name) or (keep_annotation in note.name):
            lstGooglySaveAnnotations.append(note)

    lstEnabledAnnotations = []
    for glinknote in lstGooglyLinkAnnotations:
        rangeblip = blip.range(glinknote.start, glinknote.end)
        rangeblip.clear_annotation(link_annotation)

        lstRangeSaveAnnotations = [gsavenote for gsavenote in lstGooglySaveAnnotations if IsContainsRange(glinknote, gsavenote)]

        for note in blip.annotations:
            exectype = GetExecuteType(note.name, note.value)
            if exectype != exectype_none:
                linktext = blip.text[note.start: note.end]
                rangeflg = False
                # check range
                if IsContainsRange(glinknote, note):
                    rangeflg = True
                else:
                    # 範囲外でも、範囲内のSaveAnnotation内なら含める
                    for gsavenote in lstRangeSaveAnnotations:
                        if IsInsideRange(gsavenote, note):
                            rangeflg = True
                if rangeflg:
                    pack = {
                        'uuid': uuid.uuid4().hex,
                        'mode': JudgMode(glinknote.value),
                        'exectype': exectype,
                        'oldtext': linktext,
                        'newtext': linktext,
                        'oldlength': len(linktext),
                        'newlength': len(linktext),
                        'name': note.name,
                        'value': note.value,
                        'longurl': "",
                        'shorturl': "",
                        'start': note.start,
                        'end': note.end,
                        'org_start': note.start,
                        'org_end': note.end,
                        'uuidlong': "",
                        'uuidshort': "",
                        'uuidkeep': "",
                        'delete': False,
                        'fix': False
                        }
                    lstEnabledAnnotations.append(pack)
                    #logging.debug(u"pack: %s" % (pack))

    editShortenUrl(event, wavelet, blip, lstEnabledAnnotations)


def editBlipDone(event, wavelet, blip, mode):
    """ Blip編集後にDoneを押下した場合の処理 """
    logging.debug(u"editBlipDone")

    #--------------------------------------------------
    # Delete link/auto Annotations
    #--------------------------------------------------
    lstAutoLinks = [pack for pack in blip.annotations if pack.name == "link/auto"]
    lstManualLinks = [pack for pack in blip.annotations if pack.name == "link/manual"]
    for packManual in lstManualLinks:
        for packAuto in lstAutoLinks:
            if (packAuto.start == packManual.start) and (packAuto.end == packManual.end):
                logging.debug(u"clear_annotation:auto %s : %s | %s = %s" % (packAuto.start, packAuto.end, packAuto.name, packAuto.value))
                blip.range(packAuto.start, packAuto.end).clear_annotation("link/auto") # auto

    lstEnabledAnnotations = []
    for note in blip.annotations:
        exectype = GetExecuteType(note.name, note.value)
        if exectype != exectype_none:
            linktext = blip.text[note.start: note.end]
            pack = {
                'uuid': uuid.uuid4().hex,
                'mode': mode,
                'exectype': exectype,
                'oldtext': linktext,
                'newtext': linktext,
                'oldlength': len(linktext),
                'newlength': len(linktext),
                'name': note.name,
                'value': note.value,
                'longurl': "",
                'shorturl': "",
                'start': note.start,
                'end': note.end,
                'org_start': note.start,
                'org_end': note.end,
                'uuidlong': "",
                'uuidshort': "",
                'uuidkeep': "",
                'delete': False,
                'fix': False
                }
            lstEnabledAnnotations.append(pack)
            #logging.debug(u"pack: %s" % (pack))

    editShortenUrl(event, wavelet, blip, lstEnabledAnnotations)


def editShortenUrl(event, wavelet, blip, lstEnabledAnnotations):
    """ ShortenUrlの編集処理 """
    logging.debug(u"editShortenUrl")

    #--------------------------------------------------
    # Adjust Annotations and Linking
    #--------------------------------------------------
    for packRevers in lstEnabledAnnotations:
        if packRevers['exectype'] == exectype_revers:
            logging.debug(u"packRevers: %s" % (packRevers))

            packRevers['value'] = UnpackagingSaveAnnotationValue(packRevers['value'])

            packRevers['longurl'] = packRevers['value']['longurl']
            packRevers['shorturl'] = packRevers['value']['shorturl']

            if IsMode(packRevers['value']['mode'], param_insert):
                ##################################################
                logging.debug(u"param_insert")
                findlongnote = None
                findshortnote = None
                for packLink in lstEnabledAnnotations:
                    if (packLink['exectype'] == exectype_link_ltos) or (packLink['exectype'] == exectype_link_stol):
                        if (packLink['org_start'] >= packRevers['org_start']) and (packLink['org_end'] <= packRevers['org_end']):
                            if packLink['value'] == packRevers['longurl']:
                                findlongnote = packLink
                            if packLink['value'] == packRevers['shorturl']:
                                findshortnote = packLink
                        if (findlongnote != None) and (findshortnote != None):
                            break
                # 短縮URLが存在しないとKeepの意味が無いので、短縮URLは必須とする。
                if (findlongnote != None) and (findshortnote != None):
                    logging.debug(u"case 1")
                    packRevers['uuidlong'] = findlongnote['uuid']
                    packRevers['uuidshort'] = findshortnote['uuid']

                    findlongnote['uuidkeep'] = packRevers['uuid']
                    findlongnote['longurl'] = packRevers['longurl']
                    findlongnote['shorturl'] = packRevers['shorturl']

                    findshortnote['uuidkeep'] = packRevers['uuid']
                    findshortnote['longurl'] = packRevers['longurl']
                    findshortnote['shorturl'] = packRevers['shorturl']

                elif (findlongnote == None) and (findshortnote != None):
                    logging.debug(u"case 2")
                    packRevers['uuidlong'] = ""
                    packRevers['uuidshort'] = findshortnote['uuid']

                    findshortnote['uuidkeep'] = packRevers['uuid']
                    findshortnote['longurl'] = packRevers['longurl']
                    findshortnote['shorturl'] = packRevers['shorturl']
                elif (findlongnote != None) and (findshortnote == None):
                    logging.debug(u"case 3")
                    packRevers['uuid'] = ""
                elif (findlongnote == None) and (findshortnote == None):
                    logging.debug(u"case 4")
                    packRevers['uuid'] = ""

            elif IsMode(packRevers['value']['mode'], param_textreplace):
                ##################################################
                logging.debug(u"param_textreplace")
                findnote = None
                for packLink in lstEnabledAnnotations:
                    if (packLink['exectype'] == exectype_link_ltos) or (packLink['exectype'] == exectype_link_stol):
                        if (packLink['org_start'] >= packRevers['org_start']) and (packLink['org_end'] <= packRevers['org_end']):
                            #if (packLink['oldtext'] == packRevers['shorturl']) and (packLink['value'] == packRevers['longurl']):
                            if packLink['value'] == packRevers['longurl']:
                                findnote = packLink
                                break
                if findnote != None:
                    logging.debug(u"case 1")
                    packRevers['uuidlong'] = findnote['uuid']
                    packRevers['uuidshort'] = ""

                    findnote['uuidkeep'] = packRevers['uuid']
                    findnote['longurl'] = packRevers['longurl']
                    findnote['shorturl'] = packRevers['shorturl']
                else:
                    logging.debug(u"case 2")
                    packRevers['uuid'] = ""

            elif IsMode(packRevers['value']['mode'], param_linkreplace):
                ##################################################
                logging.debug(u"param_linkreplace")
                findnote = None
                for packLink in lstEnabledAnnotations:
                    if (packLink['exectype'] == exectype_link_ltos) or (packLink['exectype'] == exectype_link_stol):
                        if (packLink['org_start'] >= packRevers['org_start']) and (packLink['org_end'] <= packRevers['org_end']):
                            #if (packLink['oldtext'] == packRevers['longurl']) and (packLink['value'] == packRevers['shorturl']):
                            if packLink['value'] == packRevers['shorturl']:
                                findnote = packLink
                                break
                if findnote != None:
                    logging.debug(u"case 1")
                    packRevers['uuidlong'] = ""
                    packRevers['uuidshort'] = findnote['uuid']

                    findnote['uuidkeep'] = packRevers['uuid']
                    findnote['longurl'] = packRevers['longurl']
                    findnote['shorturl'] = packRevers['shorturl']
                else:
                    logging.debug(u"case 2")
                    packRevers['uuid'] = ""

            elif IsMode(packRevers['value']['mode'], param_replace):
                ##################################################
                logging.debug(u"param_replace")
                findnote = None
                for packLink in lstEnabledAnnotations:
                    if (packLink['exectype'] == exectype_link_ltos) or (packLink['exectype'] == exectype_link_stol):
                        if (packLink['org_start'] >= packRevers['org_start']) and (packLink['org_end'] <= packRevers['org_end']):
                            #if (packLink['oldtext'] == packRevers['shorturl']) and (packLink['value'] == packRevers['shorturl']):
                            if packLink['value'] == packRevers['shorturl']:
                                findnote = packLink
                                break
                if findnote != None:
                    logging.debug(u"case 1")
                    packRevers['uuidlong'] = ""
                    packRevers['uuidshort'] = findnote['uuid']

                    findnote['uuidkeep'] = packRevers['uuid']
                    findnote['longurl'] = packRevers['longurl']
                    findnote['shorturl'] = packRevers['shorturl']
                else:
                    logging.debug(u"case 2")
                    packRevers['uuid'] = ""

            if packRevers['uuid'] == "":
                logging.debug(u"clear_annotation:keep")
                blip.range(packRevers['org_start'], packRevers['org_end']).clear_annotation(packRevers['name']) # keep or save

    for packLink in lstEnabledAnnotations:
        if (packLink['exectype'] == exectype_link_ltos) or (packLink['exectype'] == exectype_link_stol):
            logging.debug(u"packLink: %s" % (packLink))
            if packLink['uuidkeep'] == "":
                shortenurlservice = [service for service in ShortenUrl_Services if packLink['value'].startswith(service['url'])]
                if len(shortenurlservice) == 1:
                    #packLink['uuid'] = ""
                    logging.debug(u"link case 1")
                    packLink['longurl'] = ""
                    packLink['shorturl'] = packLink['value']
                else:
                    logging.debug(u"link case 2")
                    packLink['longurl'] = packLink['value']
                    packLink['shorturl'] = ""

    lstEnabledAnnotations = [pack for pack in lstEnabledAnnotations if pack['uuid'] != ""]
    lstEnabledAnnotations.sort(PackObjectComp)

    #logging.debug(u"lstEnabledAnnotations: %s" % (lstEnabledAnnotations))

    #--------------------------------------------------
    # Editing Blip
    #--------------------------------------------------
    logging.debug(u"Editing Blip")
    gapindex = 0
    gapcount = 0
    for packobject in lstEnabledAnnotations:
        logging.debug(u"packobject: %s" % (packobject))

        # Gap absorption
        for gapabsorption in lstEnabledAnnotations:
            if gapindex < gapabsorption['org_start']:
                gapabsorption['start'] = gapcount + gapabsorption['org_start']
            if gapindex <= gapabsorption['org_end']:
                gapabsorption['end'] = gapcount + gapabsorption['org_start'] + gapabsorption['newlength']

        logging.debug(u"org_start: %s, start: %s" % (packobject['org_start'], packobject['start']))
        logging.debug(u"org_end  : %s, end  : %s" % (packobject['org_end'], packobject['end']))

        if packobject['fix']:
            logging.debug(u"continue fix")
            continue
        packobject['fix'] = True
        gapindex = packobject['org_start']

        #--------------------------------------------------
        # delete
        #--------------------------------------------------
        if packobject['delete']:
            logging.debug(u"delete link")
            #blip.range(packobject['start'], packobject['end']).clear_annotation(packobject['name'])
            blip.range(packobject['start'], packobject['end']).delete()
            packobject['newtext'] = u""
            packobject['newlength'] = len(packobject['newtext'])

        else:
            #--------------------------------------------------
            # shorten url
            #--------------------------------------------------
            if (packobject['exectype'] == exectype_link_ltos) or (packobject['exectype'] == exectype_link_stol):
                logging.debug(u"exectype_link: %s" % (packobject['exectype']))

                if packobject['uuidkeep'] != "":
                    logging.debug(u"continue uuidkeep")
                    continue

                # URL information supplementation
                if (packobject['longurl'] != "") and (packobject['shorturl'] == ""):
                    # Get goo.gl Shorten URL
                    logging.debug(u"get_short_url")
                    packobject['shorturl'] = get_short_url(packobject['longurl'], None)
                elif (packobject['longurl'] == "") and (packobject['shorturl'] != ""):
                    # Get longer URL
                    logging.debug(u"get_long_url")
                    packobject['longurl'] = get_long_url(packobject['shorturl'], None)

                # Other service to goo.gl
                if (not packobject['shorturl'].startswith("http://goo.gl/")) and (packobject['longurl'] != ""):
                    # Get goo.gl Shorten URL
                    logging.debug(u"Other service to goo.gl get_short_url")
                    packobject['shorturl'] = get_short_url(packobject['longurl'], None)

                # Validity check
                if (packobject['longurl'] == "") or (packobject['shorturl'] == ""):
                    logging.debug(u"Validity check URL continue: L= %s : S= %s" % (packobject['longurl'], packobject['shorturl']))
                    continue

                logging.debug(u"**** mode: %s" % (packobject['mode']))
                if IsMode(packobject['mode'], param_insert):
                    ##################################################
                    textLeft = packobject['oldtext']
                    textMiddle = u" "
                    textRight = packobject['shorturl']

                    if packobject['exectype'] == exectype_link_ltos:
                        logging.debug(u"case 1")
                    elif packobject['exectype'] == exectype_link_stol:
                        if packobject['value'] == packobject['longurl']:
                            logging.debug(u"case 2")
                        else:
                            logging.debug(u"case 3")
                            textLeft = packobject['longurl']
                            textMiddle = u" "
                            textRight = packobject['shorturl']

                    packobject['newtext'] = u"%s%s%s" % (textLeft, textMiddle, textRight)
                    packobject['newlength'] = len(packobject['newtext'])
                    logging.debug(u"exectype_link_ltos - newtext: %s" % (packobject['newtext']))

                    blip.range(packobject['start'], packobject['end']).replace(textLeft)
                    blip.range(packobject['start'], packobject['start'] + len(textLeft)).insert_after(textMiddle + textRight)

                    blip.range(packobject['start'], packobject['start'] + len(textLeft)).annotate("link/manual", packobject['longurl'])

                elif IsMode(packobject['mode'], param_textreplace):
                    ##################################################
                    packobject['newtext'] = u"%s" % (packobject['shorturl'])
                    packobject['newlength'] = len(packobject['newtext'])

                    blip.range(packobject['start'], packobject['end']).replace(packobject['newtext'])
                    blip.range(packobject['start'], packobject['start'] + packobject['newlength']).annotate("link/manual", packobject['longurl'])

                elif IsMode(packobject['mode'], param_linkreplace):
                    ##################################################
                    packobject['newtext'] = u"%s" % (packobject['oldtext'])
                    packobject['newlength'] = len(packobject['newtext'])

                    blip.range(packobject['start'], packobject['end']).clear_annotation(packobject['name'])
                    blip.range(packobject['start'], packobject['start'] + packobject['newlength']).annotate("link/manual", packobject['shorturl'])

                elif IsMode(packobject['mode'], param_replace):
                    ##################################################
                    packobject['newtext'] = u"%s" % (packobject['shorturl'])
                    packobject['newlength'] = len(packobject['newtext'])

                    blip.range(packobject['start'], packobject['end']).replace(packobject['newtext'])
                    #blip.range(packobject['start'], packobject['start'] + packobject['newlength']).annotate("link/manual", packobject['shorturl'])

                # Save Annotation
                save = PackagingSaveAnnotationValue(packobject)
                blip.range(packobject['start'], packobject['start'] + packobject['newlength']).annotate(save_annotation, save)

            #--------------------------------------------------
            # revers url
            #--------------------------------------------------
            elif packobject['exectype'] == exectype_revers:
                logging.debug(u"exectype_revers")

                if (packobject['uuidlong'] == "") and ((packobject['uuidshort'] == "")):
                    logging.debug(u"continue uuidlong and uuidshort")
                    continue

                logging.debug(u"**** mode: %s" % (packobject['mode']))
                if not IsMode(packobject['mode'], param_select):
                    logging.debug(u"continue not select mode")
                    continue

                blip.range(packobject['start'], packobject['end']).clear_annotation(packobject['name']) # keep or save

                logging.debug(u"******** value.mode: %s" % (packobject['value']['mode']))
                logging.debug(u" * packobject  %s : %s" % (packobject['start'], packobject['end']))
                if IsMode(packobject['value']['mode'], param_insert):
                    ##################################################
                    longobject = FindPackObject(lstEnabledAnnotations, packobject['uuidlong'])
                    shortobject = FindPackObject(lstEnabledAnnotations, packobject['uuidshort'])

                    packobject['newtext'] = u"%s" % (packobject['value']['oldtext'])
                    #packobject['newlength'] = len(packobject['newtext'])

                    if shortobject != None:
                        if longobject != None:
                            targetobject = longobject
                            longobject['fix'] = True
                            #shortobject['fix'] = True
                            shortobject['delete'] = True

                            logging.debug(u" * longobject  %s : %s" % (longobject['start'], longobject['end']))
                            logging.debug(u" * shortobject %s : %s" % (shortobject['start'], shortobject['end']))
                        else:
                            targetobject = shortobject
                            shortobject['fix'] = True

                            logging.debug(u" * shortobject %s : %s" % (shortobject['start'], shortobject['end']))

                        blip.range(targetobject['start'], targetobject['end']).clear_annotation(targetobject['name'])
                        blip.range(targetobject['start'], targetobject['end']).replace(packobject['newtext'])
                        targetobject['newtext'] = packobject['newtext']
                        targetobject['newlength'] = len(targetobject['newtext'])

                        blip.range(targetobject['start'], targetobject['start'] + targetobject['newlength']).annotate("link/manual", packobject['value']['oldlink'])

                    packobject['newlength'] = packobject['oldlength'] - targetobject['oldlength'] + targetobject['newlength']

                elif IsMode(packobject['value']['mode'], param_textreplace):
                    ##################################################
                    targetobject = FindPackObject(lstEnabledAnnotations, packobject['uuidlong'])

                    if targetobject != None:
                        packobject['newtext'] = u"%s" % (packobject['value']['oldtext'])
                        packobject['newlength'] = len(packobject['newtext'])
                        packobject['fix'] = True

                        logging.debug(u" * targetobject %s : %s" % (targetobject['start'], targetobject['end']))

                        blip.range(targetobject['start'], targetobject['end']).clear_annotation(targetobject['name'])
                        blip.range(targetobject['start'], targetobject['end']).replace(packobject['newtext'])
                        blip.range(targetobject['start'], targetobject['start'] + packobject['newlength']).annotate("link/manual", packobject['value']['oldlink'])

                elif IsMode(packobject['value']['mode'], param_linkreplace):
                    ##################################################
                    targetobject = FindPackObject(lstEnabledAnnotations, packobject['uuidshort'])

                    if targetobject != None:
                        #packobject['newtext'] = u"%s" % (packobject['value']['oldtext'])
                        #packobject['newlength'] = len(packobject['newtext'])
                        packobject['fix'] = True

                        logging.debug(u" * targetobject %s : %s" % (targetobject['start'], targetobject['end']))

                        blip.range(targetobject['start'], targetobject['end']).clear_annotation(targetobject['name'])
                        blip.range(targetobject['start'], targetobject['start'] + packobject['newlength']).annotate("link/manual", packobject['value']['oldlink'])

                elif IsMode(packobject['value']['mode'], param_replace):
                    ##################################################
                    targetobject = FindPackObject(lstEnabledAnnotations, packobject['uuidshort'])

                    if targetobject != None:
                        packobject['newtext'] = u"%s" % (packobject['value']['oldtext'])
                        packobject['newlength'] = len(packobject['newtext'])
                        packobject['fix'] = True

                        logging.debug(u" * targetobject %s : %s" % (targetobject['start'], targetobject['end']))

                        blip.range(targetobject['start'], targetobject['end']).replace(packobject['newtext'])
                        blip.range(targetobject['start'], targetobject['start'] + packobject['newlength']).annotate("link/manual", packobject['value']['oldlink'])

        #--------------------------------------------------
        # calc gap
        #--------------------------------------------------
        gapcount += (packobject['newlength'] - packobject['oldlength'])



def FindPackObject(lstEnabledAnnotations, uuid):
    packobject = None
    if uuid != "":
        for pack in lstEnabledAnnotations:
            if pack['uuid'] == uuid:
                packobject = pack
                break
    return packobject

def PackagingSaveAnnotationValue(pack):
    save = u",".join([
        unicode(pack['mode']),
        unicode(pack['name']),
        base64.b64encode(pack['oldtext'].encode("utf-8")),
        base64.b64encode(pack['newtext'].encode("utf-8")),
        base64.b64encode(pack['longurl'].encode("utf-8")),
        base64.b64encode(pack['shorturl'].encode("utf-8")),
        base64.b64encode(pack['value'].encode("utf-8")) #oldlink
        ])
    logging.debug(u"PackagingSaveAnnotationValue : %s" % save)
    return save

def UnpackagingSaveAnnotationValue(save):
    pack = None
    if isinstance(save, basestring):
        csv = save.split(',')
        pack = {
            'mode': int(csv[0]),
            'name': unicode(csv[1]),
            'oldtext': unicode(base64.b64decode(csv[2]), "utf-8"),
            'newtext': unicode(base64.b64decode(csv[3]), "utf-8"),
            'longurl': unicode(base64.b64decode(csv[4]), "utf-8"),
            'shorturl': unicode(base64.b64decode(csv[5]), "utf-8"),
            'oldlink': unicode(base64.b64decode(csv[6]), "utf-8")
            }
    else:
        # old keep annotation
        pack = {
            'mode': int(save['mode']),
            'name': unicode(save['name']),
            'oldtext': unicode(save['oldtext']),
            'newtext': unicode(save['newtext']),
            'longurl': unicode(save['longurl']),
            'shorturl': unicode(save['shorturl']),
            'oldlink': unicode(save['longurl'])  # dummy
            }
    logging.debug(u"UnpackagingSaveAnnotationValue : %s" % pack)
    return pack

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

def IsContainsRange(range, target):
    """ 選択範囲に重なっているか判定する処理 """
    ret = False
    if (target.start <= range.start) and (target.end >= range.end):
        ret = True
    if (target.start >= range.start) and (target.start < range.end):
        ret = True
    if (target.end >= range.start) and (target.end <= range.end):
        ret = True
    return ret

def IsInsideRange(range, target):
    """ 選択範囲に入っているか判定する処理 """
    ret = False
    if (target.start >= range.start) and (target.end <= range.end):
        ret = True
    return ret

def GetExecuteType(notename, notelink):
    """ ShortenURLの実行対象か判定する処理 """
    ret = exectype_none
    if "link/auto" in notename:
        shortenurlservice = [service for service in ShortenUrl_Services if notelink.startswith(service['url'])]
        if len(shortenurlservice) == 1:
            ret = exectype_link_stol
        else:
            ret = exectype_link_ltos
    elif "link/manual" in notename:
        shortenurlservice = [service for service in ShortenUrl_Services if notelink.startswith(service['url'])]
        if len(shortenurlservice) == 1:
            ret = exectype_link_stol
        else:
            ret = exectype_link_ltos
    elif "link/wave" in notename:
        logging.debug(u"link/wave : %s" % notelink)
        #exectype_linkでもOKだと思う
        ret = exectype_none
    elif link_annotation in notename:
        ret = exectype_none
    elif keep_annotation in notename:
        ret = exectype_revers
    elif save_annotation in notename:
        ret = exectype_revers
    else:
        ret = exectype_none
    return ret

def GetProxyingFor(wavelet):
    """ Robotのパラメータ取得 """
    logging.debug(u"robot_address: %s" % wavelet.robot_address)
    robotid = wavelet.robot_address.split('@')[0]
    if '#' in robotid:
        robotid = robotid.split('#')[0]
    logging.debug(u"robotid: %s" % robotid)
    if '+' in robotid:
        proxyingFor = robotid.split('+', 1)[1].lower()
    else:
        proxyingFor = ""
    logging.debug(u"GetProxyingFor() proxyingFor: %s" % proxyingFor)
    return proxyingFor

def PackObjectComp(x, y):
    ret = cmp(x['org_start'], y['org_start'])
    if ret == 0:
        ret = cmp(x['exectype'], y['exectype'])
        if ret == 0:
            ret = cmp(x['org_end'], y['org_end'])
    return ret


def get_long_url(shorturi, user):
    # urlopen BUG? It is NG including "#".
    #   NG: http://goo.gl/z1d5
    #   OK: http://goo.gl/WGdK
    #req = urllib2.Request(shorturi)
    #conn = urllib2.urlopen(req)
    #long_url = conn.geturl()
    # RFC BUG....
    # http://www.w3.org/Protocols/HTTP/1.1/rfc2616bis/issues/#i6
    long_url = ""
    try:
        shortenurlservices = [service for service in ShortenUrl_Services if shorturi.startswith(service['url'])]
        if len(shortenurlservices) == 1:
            service = shortenurlservices[0]
            getstr = u"/%s" % (shorturi.replace(service['url'], ""))

            conn = httplib.HTTPConnection(service['domain'])
            conn.request("GET", getstr)
            res = conn.getresponse()
            if res.status == service['status']:
                location = res.getheader("Location", "")
                if shorturi != location:
                    long_url = location
                else:
                    long_url = ""
                    logging.debug(u"longer: same url: %s" % (location))
            else:
                long_url = ""
                logging.debug(u"longer: Status is a disagreement: %s" % (res.status))
        else:
            long_url = ""
            logging.warning(u"longer: not goo.gl")
        logging.debug(u"longer\n S-URL: %s\n L-URL: %s" % (shorturi, long_url))
    except:
        long_url = ""
        logging.warning(u"longer\n S-URL: %s\n L-URL: Exception: %s" % (shorturi, sys.exc_info()[0]))
    return long_url

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
    myRobot = robot.Robot(__appname__, image_url=__image_url__, profile_url=__profile_url__)
    myRobot.register_handler(events.WaveletSelfAdded, OnWaveletSelfAdded, context=[events.Context.ALL])
    myRobot.register_handler(events.DocumentChanged, OnDocumentChanged, context=[events.Context.SELF])
    myRobot.register_handler(events.AnnotatedTextChanged, OnAnnotatedTextChanged, context=[events.Context.SELF], filter=".*goo-gly.*")
    myRobot.register_handler(events.BlipSubmitted, OnBlipSubmitted, context=[events.Context.SELF])
    myRobot.register_handler(events.OperationError, OnOperationError)
    appengine_robot_runner.run(myRobot, debug=True)

