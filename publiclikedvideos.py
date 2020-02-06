# -*- coding: utf-8 -*-

# Sample Python code for youtube.playlists.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/guides/code_samples#python

# Copyright (c) 2020, Ben Cantrick
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os
import sys
import json
import time
import pprint
import collections

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


# This is the name of the playlist you want your Liked Videos mirrored to. Not case sensitive.
__publicLikedVideosPlaylistName = "Liked Videos (PUBLIC)"


def addVids(apiResponse, vDict):
    # print('Num vids found this time = ' + str(len(apiResponse['items'])) )
    for vidNum in range(0, len(apiResponse['items']) ):
        vidInfo = apiResponse['items'][vidNum]['snippet']
        vDict[vidInfo['resourceId']['videoId']] = vidInfo['title']


def fetchAllVidsOnPlaylist(ytApi, playlistId, vidDict):
    request = ytApi.playlistItems().list(             # Fetch the first 50
        part='id,snippet',
        playlistId=playlistId,
        maxResults=50
    )
    response = request.execute()

    print('\nNumber of videos on list = ' + str(response['pageInfo']['totalResults']) )
    addVids(response, vidDict)

    while 'nextPageToken' in response:                # Gotta fetch 'em all!
        request = ytApi.playlistItems().list(
            part='id,snippet',
            playlistId=playlistId,
            maxResults=50,
            pageToken=response['nextPageToken']
        )
        response = request.execute()
        addVids(response, vidDict)

    print('Total vids found = ' + str(len(vidDict)) )
    pprint.pprint(vidDict, sort_dicts=False, width=120)



def copyVidsToPlaylist(ytApi, playlistId, vDict):

    for id in vDict:
        print('Adding ' + id + ' "'  + vDict[id] + '" ...')
        time.sleep(0.5)

        try:
            request = ytApi.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlistId,
                        "position": 0,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": id
                        }
                    }
                }
            )
            response = request.execute()

        except googleapiclient.errors.HttpError as httpe:
            print("ERROR: {0}".format(httpe))     # Not much we can do except acknowledge and move on.

        #print(response)



def main():

    # Give location of OATH2 creds file, and specify what kind of actions we want to take ("scopes").
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        'client_secret.json',
        scopes = ['https://www.googleapis.com/auth/youtube.force-ssl'] )

    print('\nAttempting to authenticate...\n')
    # Force user to authorize via web browser, cutting and pasting new auth code every time.
    creds = flow.run_console()

    # Create a "service object" that will allow us to talk with the YouTube API webservers.
    ytApiSO = googleapiclient.discovery.build('youtube', 'v3', credentials=creds)

    print('\nFetching channel info.')

    # Issue a request to fetch info about the channel's special playlists: "likes", "favorites", etc.
    request = ytApiSO.channels().list(
        part='snippet,contentDetails',
	mine=True,        # Access channel given by client_secrets.json. Requires correct auth creds, obvs.
        maxResults=50     # Maximum allowed by API spec at time of code being written.
    )
    response = request.execute()

    print()
    chInfo = response['items'][0]
    likedPlaylistId = chInfo['contentDetails']['relatedPlaylists']['likes']
    print('Channel name = "' + chInfo['snippet']['title'] + '", id = ' + chInfo['id'])
    print('Private "Liked Videos" playlist id = ' + likedPlaylistId)

    print('Other playlists and their ids:')

    # Issue a request to fetch info about public playlists on the channel.
    request = ytApiSO.playlists().list(
        part='snippet,contentDetails',
	mine=True,
        maxResults=50
    )
    response = request.execute()

    plvPlaylistId = None
    plvPlaylistName = None
    for plist in response['items']:
        title = plist['snippet']['title']
        print('"' + title + '" = ' + plist['id'])
        if title.lower() == __publicLikedVideosPlaylistName.lower():
            plvPlaylistName = title
            plvPlaylistId = plist['id']

    if plvPlaylistId is None:
      sys.exit("\nCouldn't find a \"" + __publicLikedVideosPlaylistName + '" playlist. Abort!')
    print('\nFound "' + plvPlaylistName + '", id = ' + plvPlaylistId)

    print('\nYoinking private "Liked Videos" titles and ids.')
    likedVidsDict = {}   
    fetchAllVidsOnPlaylist(ytApiSO, likedPlaylistId, likedVidsDict)

    print('\nYoinking "' + plvPlaylistName + '" titles and ids.')
    publicVidsDict = {}   
    fetchAllVidsOnPlaylist(ytApiSO, plvPlaylistId, publicVidsDict)

    # Any video in both the Public and Private dict was already copied, ignore it.
    tempDict = {}
    for id in likedVidsDict:
        if id not in publicVidsDict:
            tempDict[id] = likedVidsDict[id]

    # In Python 3.7+, dicts remember the order of insertion and so this will actually
    # reverse the order of the entries. Before that, it's just an expensive noop.
    vidsToAdd = {}
    for key, val in reversed(tempDict.items()):
        vidsToAdd[key] = val

    print('\nReady to add ' + str(len(vidsToAdd)) + ' videos to "' + plvPlaylistName + '"')
    pprint.pprint(vidsToAdd, sort_dicts=False, width=120)

    input("\nPress Enter to continue. (Or press CTRL-C to stop, YOU MANIACS! YOU BLEW IT UP! AH, DAMN YOU! GOD DAMN YOU ALL TO HELL!)")

    copyVidsToPlaylist(ytApiSO, plvPlaylistId, vidsToAdd)

    print("Done!")

if __name__ == "__main__":
    main()
