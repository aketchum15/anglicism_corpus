import argparse
import json
import os
import pickle
import time 
import xml
import traceback

from youtube_transcript_api import YouTubeTranscriptApi, _errors as YouTubeTranscriptErrors 

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

class ChannelScraper():
    '''
    Iterator class to scrape all videos from a given channel
    '''
    def __init__(self, channelId, pageToken=None):

        self.NUM_RESULTS = 50
        self.channelId = channelId
        self.done = False

        if pageToken is not None:
            self.pageToken = pageToken
        else:
            self.pageToken = None

    def __iter__(self):
        request = Youtube.channels().list(
            part="contentDetails",
            id=self.channelId
        )
        # if we cannot find the playlist then we cannot make the iterator
        try:
            response = request.execute()
        except Exception as e:
            self.done = True
            return iter([])

        # get the uoloads playlist ID for given channel
        self.uploadsId = response['items'][0]['contentDetails']['relatedPlaylists']['uploads'] 
        return self

    def __next__(self) -> list[dict]:
        
        if self.done:
            raise StopIteration

        # get the videos from channel's uploads playlsit 
        request = Youtube.playlistItems().list(
            part="contentDetails",
            playlistId=self.uploadsId,
            pageToken=self.pageToken,
            maxResults=self.NUM_RESULTS
        )

        # assume all errors are 401s and end iteration
        # TODO: don't assume that 
        try:
            response = request.execute()
        except Exception as e:
            print(f'Error getting playlist items: {e}')
            raise StopIteration

        videoIds = [item['contentDetails']['videoId'] for item in response['items']]

        # get the next page token to update the iterator with later
        if 'nextPageToken' in response.keys():
            (nextPageToken, ) = response['nextPageToken'],
        else:
            nextPageToken = None

        transcripts = []
        for id in videoIds[:]:
            try:
                # get all available transcripts
                l = YouTubeTranscriptApi.list_transcripts(id)
            except YouTubeTranscriptErrors.TranscriptsDisabled:
                print(f'Transcripts are disabled for video: {id}. skipping...');
                videoIds.remove(id)
                continue
            try:
                # check if there is german
                response = l.find_transcript(['de']).fetch()
            except YouTubeTranscriptErrors.NoTranscriptFound:
                print(f'No German transcript for video: {id}. skipping...');
                videoIds.remove(id)
                continue
            # https://github.com/jdepoix/youtube-transcript-api/issues/320
            # there seems to be no solution for this intermittent issue yet
            # for now wait 10 seconds and then retry the whole process.
            # 10 seconds is probably overkill but it works.
            except xml.etree.ElementTree.ParseError:
                print('weird xml error happened. retrying...')
                time.sleep(10)
                try:
                    l = YouTubeTranscriptApi.list_transcripts(id)
                except YouTubeTranscriptErrors.TranscriptsDisabled:
                    print(f'Transcripts are disabled for video: {id}. skipping...');
                    videoIds.remove(id)
                    continue
                try:
                    response = l.find_transcript(['de']).fetch()
                except YouTubeTranscriptErrors.NoTranscriptFound:
                    print(f'No German transcript for video: {id}. skipping...');
                    videoIds.remove(id)
                    continue
                except xml.etree.ElementTree.ParseError:
                    print('retry failed. skipping...')


            # add the transcript to the list 
            print(f'Successfully downloaded transcript for video: {id}')
            transcript = ' '.join([i['text'] for i in response])
            transcripts.append(transcript)

        # get the video metadata (category and title)
        request = Youtube.videos().list(
            part="snippet",
            id=videoIds,
            maxResults=self.NUM_RESULTS
        )
        try:
            response = request.execute()
        except Exception as e:
            print(f'Error getting video data: {e}')
            raise StopIteration

        titles = [item['snippet']['title'] for item in response['items']]
        categoryIds = [item['snippet']['categoryId'] for item in response['items']]

        # get the actual names from the category ids 
        categories = []
        for id in categoryIds:
            request = Youtube.videoCategories().list(
                part="snippet",
                id=id
            )

            try:
                response = request.execute()
                categories.extend([item['snippet']['title'] for item in response['items']])
            except Exception as e:
                print(f'Error getting video category data: {e}')
                raise StopIteration
    
        videoData = []
        # create dictionaries for each video with the title, category and transcript
        for transcript, category, title in zip(transcripts, categories, titles):
            videoData.append({'title': title, 'category': category, 'transcript': transcript})

        # update the page token 
        self.pageToken = nextPageToken

        # if there wasn't a next page token, we are done
        if not nextPageToken:
            self.done = True

        return videoData


def save_progress(out: dict, failed: ChannelScraper|None):

    print('saving progress...')
    with open(f'output/{out["id"]}.json', 'w') as f:
        json.dump(out, f, ensure_ascii=False)

    if ChannelScraper is not None:
        with open('output/progress.pkl', 'wb') as f:
            pickle.dump(failed, f)


def load_progress() -> tuple[dict, ChannelScraper]|None:
    if os.path.exists('output/progress.pkl'):
        with open('output/progress.pkl', 'rb') as scraper_file:
            s = pickle.load(scraper_file)
            if s is None:
                return None
            if os.path.exists(f'output/{s.channelId}.json'):
                with open(f'output/{s.channelId}.json', 'r') as output_file:
                    out = json.load(output_file)
            else:
                print(f'Warning: output file not found for partially scraped channel "{s.channelId}". Possible loss of data.')
                out = {'id': s.channelId, 'transcripts': []}
            return (out, s)
    return None

def scrape_channel(s: ChannelScraper, out: dict|None = None) -> bool:

    if out is None:
        out = {'id': s.channelId, 'transcripts': []}

    try:
        for v in s: 
            out['transcripts'].extend(v)
    except:
        print(f'Error occurred while scraping channel: {s.channelId}')
        traceback.print_exc()
        save_progress(out, s)
        return False
    else:
        if not s.done:
            print(f'Reached quota limit while scraping channel: {s.channelId}.')
            save_progress(out, s)
        else:
            print(f'Finished scraping channel: {s.channelId}')
            save_progress(out, None)

        return s.done

def main(file: str) -> None:

    # make sure inputted file exists
    if not os.path.exists(file):
        print(f'error: file "{file}" not found!')
        return

    # load list of channels from file
    channels = []
    with open(file, 'r') as f:
        channels = [line.strip() for line in f]

    # load progress if there is any
    start_index = 0
    loaded = load_progress()
    # if there is a partially finished channel, we need to scrape it
    if loaded is not None:
        (out, last) = loaded
        try:
            # save the index of the channel after the partially completed one 
            start_index = channels.index(last.channelId)+1
        except ValueError:
            print(f'Warning: saved channel id "{last.channelId}" not found in file "{file}". will continue from the beginning of channels file after scraping channel "{last.channelId}".')

        if not scrape_channel(last, out):
            start_index = len(channels)

    # continue scraping channels from the file 
    for i in range(start_index, len(channels)):
        s = ChannelScraper(channels[i])
        if not scrape_channel(s):
            break;

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='Corpus Scraper')
    parser.add_argument('channels', type=str, action='store',
                        help='file containing a list of channel ids separated by newlines')
    args = parser.parse_args()

    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "secret.json"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    flow.run_local_server()
    credentials = flow.credentials
    Youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    main(args.channels)
