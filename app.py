from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from config import WebshareConfig
import re
import logging
import os
from logging.handlers import RotatingFileHandler

# Set up logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if not match:
        raise ValueError("Nieprawidłowy URL YouTube")
    return match.group(1)

def get_transcript(video_id):
    """Get transcript using a static proxy"""
    try:
        proxy = WebshareConfig.get_proxy()
        if proxy:
            logger.info(f"Using proxy: {WebshareConfig.PROXY_ADDRESS}:{WebshareConfig.PROXY_PORT}")
            logger.info(f"Full proxy configuration: {proxy}")  # Added for debugging
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['pl', 'en'],
                proxies=proxy
            )
            logger.info("Successfully retrieved transcript with proxy")
            return transcript
        else:
            logger.warning("No proxy configuration available, attempting without proxy")
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pl', 'en'])
            logger.info("Successfully retrieved transcript without proxy")
            return transcript

    except Exception as e:
        logger.error(f"Failed to get transcript: {str(e)}")
        raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_transcript', methods=['POST'])
def get_transcript_route():
    try:
        url = request.get_json().get('url')
        if not url:
            return jsonify({'error': 'URL jest wymagany'}), 400

        video_id = extract_video_id(url)
        logger.info(f"Processing video ID: {video_id}")

        transcript_data = get_transcript(video_id)
        
        # Format transcript with timestamps
        formatted_transcript = []
        for entry in transcript_data:
            start_time = int(entry['start'])
            minutes = start_time // 60
            seconds = start_time % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            text = entry['text']
            formatted_transcript.append(f"{timestamp} {text}")

        return jsonify({
            'video_id': video_id,
            'transcript': '\n'.join(formatted_transcript)
        })

    except ValueError as e:
        logger.warning(f"Invalid input: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in route: {str(e)}")
        # Return the actual error message instead of generic message
        return jsonify({'error': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)