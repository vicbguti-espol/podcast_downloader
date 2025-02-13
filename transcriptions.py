import os
import json
import time
import requests
from podcast import Podcast
import sys

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

def create_transcripts(podcast_list, **kwargs):
	all_transcription_metadata = {}
	for podcast in podcast_list:
		podcast_metadata = {}
		downloads = os.listdir(podcast.download_directory)
		for download in downloads:
			print("Uploading", download)
			file_path = f'{podcast.download_directory}/{download}'
			content_url = upload_to_assembly_ai(file_path)
			transcription_id = transcribe_podcast(content_url, **kwargs)
			podcast_metadata[download] = transcription_id

		all_transcription_metadata[podcast.name] = podcast_metadata.copy()

	return all_transcription_metadata

def upload_to_assembly_ai(file_path):
	headers = {'authorization': os.getenv('ASSEMBLY_AI_KEY')}
	endpoint = 'https://api.assemblyai.com/v2/upload'
	response = requests.post(endpoint, headers=headers, data=read_file(file_path))
	upload_url = response.json()['upload_url']
	return upload_url

def transcribe_podcast(url, **kwargs):
	headers = {
		"authorization": os.getenv('ASSEMBLY_AI_KEY'),
	    "content-type": "application/json",
	}
	
	json = {'audio_url': url}
	for key, value in kwargs.items():
		json[key] = value

	print(json)
	endpoint = 'https://api.assemblyai.com/v2/transcript'
	response = requests.post(endpoint, headers=headers, json=json)
	transcription_id = response.json()['id']
	return transcription_id

def read_file(filename, chunk_size=5242880):
    with open(filename, 'rb') as _file:
        while True:
            data = _file.read(chunk_size)
            if not data:
                break
            yield data

def save_transcription_metadata(metadata, file_path='./Podcast-Downloader/transcripts/metadata.json'):
	with open(file_path,'w') as f:
		json.dump(metadata, f)

def load_json(file_path):
	with open(file_path) as json_file:
		dictionary = json.load(json_file)
	return dictionary

def save_transcriptions_locally(podcast_list):
	# Load transcription metadata
	metadata = load_json('./Podcast-Downloader/transcripts/metadata.json')
	for podcast in podcast_list:
		podcast_transcriptions = metadata[podcast.name]
		for episode, transcription_id in podcast_transcriptions.items():
			episode_name = os.path.splitext(episode)[0]
			output_path = f'{podcast.transcription_directory}/{episode_name}.json'
			print('Trying to save', output_path)
			paragraphs = wait_and_get_assembly_ai_transcript(transcription_id)
			with open(output_path, 'w') as f:
				json.dump(paragraphs, f)

def get_assembly_ai_transcript(transcription_id):
	headers = {'authorization': os.environ['ASSEMBLY_AI_KEY']}
	endpoint = f'https://api.assemblyai.com/v2/transcript/{transcription_id}/paragraphs'
	response = requests.get(endpoint, headers=headers)
	return response

def get_podcast_list(raw_podcast_list):
	podcast_list = []

	for raw_podcast in raw_podcast_list:
		podcast_list += [Podcast(raw_podcast['name'], raw_podcast['rss_feed_url'])]
	
	return podcast_list

def wait_and_get_assembly_ai_transcript(transcription_id):
	while True:
		response = get_assembly_ai_transcript(transcription_id)
		if response.status_code == 200:
			print("Got transcript")
			break
		elif response.status_code == 404:
			print("Error getting transcript")
			break
		else:
			print("Transcript not available, trying again in 10 seconds...")
			time.sleep(10) # Try again in 10 seconds

	return response.json()


if __name__ == '__main__':
	print("\n--- Transcribing podcasts... ---\n")

	# Obtener el podcast_list
	base_dir = './Podcast-Downloader'
	podcast_list_dir = f'{base_dir}/podcast_list.json'
	
	raw_podcast_list = load_json(podcast_list_dir)['podcast_list']
	podcast_list = get_podcast_list(raw_podcast_list)

	metadata = create_transcripts(podcast_list, audio_start_from=600000, audio_end_at=900000, language_code="es")
	print('Uploaded transcripts')
	save_transcription_metadata(metadata)
	save_transcriptions_locally(podcast_list)