import os
import re
import shutil
import sys
import time
import random

import youtube_dl
from internetarchive import get_item, upload
from TikTokApi import TikTokApi
#Make sure to change to 'from .argparser import parse_args' when uploading
from argparser import parse_args


api = TikTokApi()

def getVersion():
    return '2020.12.26'


def getUsernameVideos(username, limit):
    if limit is not None:
        count = int(limit)
    else:
        count = 9999
    tiktoks = api.byUsername(username, count=count)
    return tiktoks


def getHashtagVideos(hashtag, limit):
    if limit is not None:
        count = int(limit)
    else:
        count = 9999
    tiktoks = api.byHashtag(hashtag, count=count)
    return tiktoks


def getLikedVideos(username, limit):
    if limit is not None:
        count = int(limit)
    else:
        count = 9999
    tiktoks = api.userLikedbyUsername(username, count=count)
    return tiktoks

def downloadTikTok(username, tiktok, cwd, varTry, did):
    try:
        tiktokID = tiktok['id']
    except:
        try:
            tiktokID = tiktok['itemInfos']['id']
        except:
            tiktokID = tiktok['itemInfo']['itemStruct']['id']
    ydl_opts = {
        'writeinfojson': True,
        'writedescription': True,
        'write_all_thumbnails': True,
        'writeannotations': True,
        'allsubtitles': True,
        'ignoreerrors': True,
        'fixup': True,
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,
        'outtmpl': tiktokID + '.mp4',
    }
    if not os.path.exists(tiktokID):
        os.mkdir(tiktokID)
    os.chdir(tiktokID)
    if varTry % 3 != 0:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            # ydl.download([tiktok['itemInfo']['itemStruct']['video']['downloadAddr']])
            ydl.download(['https://www.tiktok.com/@' + username + '/video/' + tiktokID])
    else:
        mp4 = open(tiktokID + '.mp4', "wb")
        mp4.write(api.get_Video_By_DownloadURL(tiktok['video']['downloadAddr'], custom_did=did))
        mp4.close()
        #shutil.rmtree('tmp')
    try:
        mp4 = open(tiktokID + '.mp4', "r", encoding="latin-1")
        # For some reason, ytdl sometimes downloads the HTML page instead of the video
        # this removes the HTML
        check = str(mp4.read())[:15]
        if (check == '<!DOCTYPE html>') or (check[:6] == '<HTML>'):
            mp4.close()
            os.remove(tiktokID + '.mp4')
        else:
            mp4.close()
    except FileNotFoundError:
        pass
    x = os.listdir()
    for i in x:
        if i.endswith('.unknown_video'):
            base = os.path.splitext(i)[0]
            if os.path.exists(base + '.mp4'):
                os.remove(base + '.mp4')
            os.rename(i, base + '.mp4')
    json = open("tiktok_info.json", "w", encoding="utf-8")
    json.write(str(tiktok))
    json.close()
    os.chdir(cwd)


def uploadTikTok(username, tiktok, deletionStatus, file):
    regex = re.compile('[0-9]{17}')
    regexA = re.compile('[0-9]{18}')
    regexB = re.compile('[0-9]{19}')
    regexC = re.compile('[0-9]{8}')
    regexD = re.compile('[0-9]{9}')
    if os.path.isdir(tiktok):
        if (
            regex.match(str(tiktok))
            or (regexA.match(str(tiktok)))
            or (regexB.match(str(tiktok)))
            or (regexC.match(str(tiktok)))
            or (regexD.match(str(tiktok)))
        ):  # TODO: use or regex with "|" instead of this
            item = get_item('tiktok-' + tiktok)
            if username is None:
                if file is not None:
                    file.write(str(tiktok))
                    file.write('\n')
                return None
            item.upload(
                './' + tiktok + '/',
                verbose=True,
                checksum=True,
                delete=deletionStatus,
                metadata=dict(
                    collection='opensource_media',
                    subject='tiktok',
                    creator=username,
                    title='TikTok Video by ' + username,
                    originalurl='https://www.tiktok.com/@' + username + '/video/' + tiktok,
                    scanner='TikUp ' + getVersion(),
                ),
                retries=9001,
                retries_sleep=60,
            )
            if deletionStatus:
                os.rmdir(tiktok)
            print()
            print('Uploaded to https://archive.org/details/tiktok-' + tiktok)
            print()
            if file is not None:
                file.write(str(tiktok))
                file.write('\n')


def downloadTikToks(username, tiktoks, file, downloadType, did):
    cwd = os.getcwd()
    try:
        lines = file.readlines()
        for x in range(0, len(lines)):
            lines[x] = lines[x].replace('\n', '')
    except:
        lines = ''
    ids = []
    for tiktok in tiktoks:
        if file is not None and doesIdExist(lines, tiktok['id']):
            print(tiktok['id'] + " has already been archived.")
        else:
            username = tiktok['author']['uniqueId']
            if username is None:
                print(tiktok['id'] + ' has been deleted or is private')
                ids.append(tiktok['id'])
            else:
                downloadTikTok(username, tiktok, cwd, 1, did)
                i = 1
                while not os.path.exists(tiktok['id'] + '/' + tiktok['id'] + '.mp4'):
                    tiktokObj = getTikTokObject(tiktok, did)
                    username = tiktokObj['itemInfo']['itemStruct']['author']['uniqueId']
                    time.sleep(1)
                    downloadTikTok(username, tiktokObj['itemInfo']['itemStruct'], cwd, i, did)
                    i += 1
                print(tiktok['id'] + ' has been downloaded')
                ids.append(tiktok['id'])
    return ids


def uploadTikToks(tiktoks, file, delete):
    for tiktok in tiktoks:
        uploadTikTok(getUsername(tiktok), tiktok, delete, file)


def doesIdExist(lines, tiktok):
    return tiktok in lines


def getUsername(tiktokId):
    thing = api.getTikTokById(tiktokId)
    try:
        return thing['itemInfo']['itemStruct']['author']['uniqueId']
    except:
        return None


def getTikTokObject(tiktokId, did):
    thing = api.getTikTokById(tiktokId, custom_did=did)
    return thing


def main():
    os.chdir(os.path.expanduser('~'))
    if not os.path.exists('./.tikup'):
        os.mkdir('./.tikup')
    os.chdir('./.tikup')

    args = parse_args()
    username = args.user
    delete = args.no_delete
    limit = args.limit
    archive = args.use_download_archive

    downloadType = ''
    if archive:
        try:
            file = open('archive.txt', 'r+')
        except FileNotFoundError:
            f = open('archive.txt', 'x')
            f.close()
            file = open('archive.txt', 'r+')
    else:
        file = None
    did = str(random.randint(10000, 999999999))
    if args.hashtag:  # Download hashtag
        downloadType = 'hashtag'
        tiktoks = getHashtagVideos(username, limit)
    elif args.id:  # Download user ID
        downloadType = 'id'
        tiktoks = [username]
    elif args.liked:  # Download liked
        downloadType = 'liked'
        tiktoks = getLikedVideos(username, limit)
    else:  # Download username
        downloadType = 'username'
        tiktoks = getUsernameVideos(username, limit)
    tiktoks = downloadTikToks(username, tiktoks, file, downloadType, did)
    if args.no_upload:  # Upload to IA
        uploadTikToks(tiktoks, file, delete)

    try:
        file.close()
    except:
        pass
    print('')


if __name__ == "__main__":
    main()
