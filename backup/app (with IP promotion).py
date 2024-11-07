from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from config import WebshareConfig
import re
import logging
import os
from logging.handlers import RotatingFileHandler
import time

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
    """Get transcript with multiple attempts using different proxies"""
    try:
        # Get list of all available proxies
        proxy_list = WebshareConfig.get_proxy_list()
        logger.info(f"Got {len(proxy_list)} proxies available")
        
        # Try each proxy
        used_proxies = set()
        max_attempts = min(3, len(proxy_list))
        
        for attempt in range(max_attempts):
            # Filter out already used proxies
            available_proxies = [p for p in proxy_list if p['address'] not in used_proxies]
            if not available_proxies:
                logger.warning("No more unique proxies available")
                break
                
            # Get a proxy with preference for successful ones
            proxy = WebshareConfig.get_random_proxy(available_proxies)
            if proxy:
                proxy_address = proxy['address']
                used_proxies.add(proxy_address)
                
                try:
                    logger.info(f"Attempt {attempt + 1}/{max_attempts} using proxy: {proxy_address}")
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id,
                        languages=['pl', 'en'],
                        proxies=proxy
                    )
                    # Update proxy stats with success
                    WebshareConfig.update_proxy_stats(proxy_address, success=True)
                    logger.info(f"Successfully retrieved transcript with proxy: {proxy_address}")
                    return transcript
                except Exception as e:
                    # Update proxy stats with failure
                    WebshareConfig.update_proxy_stats(proxy_address, success=False)
                    logger.warning(f"Proxy attempt {attempt + 1} with {proxy_address} failed: {str(e)}")
                    # Add small delay before next attempt
                    time.sleep(1)
            else:
                logger.warning(f"No proxy available for attempt {attempt + 1}")

        # If all proxy attempts fail, try without proxy
        logger.info("All proxy attempts failed or no proxies available, attempting without proxy")
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
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Wystąpił nieoczekiwany błąd'}), 500

if __name__ == '__main__':
    app.run(debug=True)