from flask import Flask, request, jsonify, render_template, send_from_directory
from api_functions import ApiFunc
import os
import logging
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from googleapiclient.discovery import build


app = Flask(__name__)
CORS(app)
app.logger.setLevel(logging.DEBUG)

SWAGGER_URL = '/api/docs'
API_URL = '/swagger.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Media Downloader API"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/swagger.yaml')
def swagger():
    with open('swagger.yaml', 'r') as f:
        return f.read(), 200, {'Content-Type': 'text/yaml'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/youtube')
def youtube_search_page():
    return render_template('youtube.html', active_tab='youtube')

@app.route('/yandex')
def yandex_search_page():
    return render_template('yandex.html', active_tab='yandex')

@app.route('/vk')
def vk_search_page():
    return render_template('vk.html', active_tab='vk')

@app.route('/api/download', methods=['POST'])
def api_download():
    
    if request.content_type == 'application/json':
        data = request.get_json()
    elif request.content_type in ['application/x-www-form-urlencoded', 'multipart/form-data']:
        data = request.form
    else:
        try:
            data = request.get_json(force=True)
        except:
            data = request.form

    if not data:
        app.logger.error("No data received")
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    url = data.get('url')
    media_type = data.get('type', data.get('media_type', 'video'))
    format = data.get('format', 'mp4' if media_type == 'video' else 'mp3')

    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400

    try:
        if 'yandex' in url.lower():
            media_type = 'audio'
            format = 'mp3'

        result = ApiFunc.download_media(url, format)

        if result.get('success'):
            filename = os.path.basename(result['path'])

            return jsonify({
                'success': True,
                'path': f'/downloads/{filename}',
                'filename': filename
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        app.logger.exception("Download error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/youtube/search', methods=['GET'])
def api_youtube_search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    results = ApiFunc.parse_youtube_videos_by_name(query)
    return jsonify(results)

@app.route('/api/yandex/search', methods=['GET'])
def api_yandex_search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    results = ApiFunc.parse_yandex_tracks_by_name(query)
    return jsonify(results)


@app.route('/downloads/<path:filename>')
def download_file(filename):
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    yandex_dir = os.path.join(downloads_dir, "YandexMusic")
    
    for directory in [downloads_dir, yandex_dir]:
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            return send_from_directory(directory, filename, as_attachment=True)
    
    return jsonify({'error': 'File not found'}), 404


@app.route('/api/youtube/video', methods=['GET'])
def api_youtube_video_by_url():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400
    
    results = ApiFunc.find_youtube_video_by_url(url)
    return jsonify(results)


@app.route('/api/yandex/track', methods=['GET'])
def api_yandex_track_by_url():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400
    
    result = ApiFunc.find_yandex_music_track_by_url(url)
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Track not found'}), 404


@app.route('/api/youtube/trending')
def api_youtube_trending():
    results = ApiFunc.get_youtube_trending_videos()
    return jsonify(results)

@app.route('/api/yandex/popular')
def api_yandex_popular():
    results = ApiFunc.get_yandex_popular_tracks()
    return jsonify(results)


@app.route('/api/youtube/channels', methods=['GET'])
def api_youtube_channels():
    """Поиск каналов по названию"""
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    try:
        youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        response = youtube.search().list(
            part='snippet',
            maxResults=10,
            q=query,
            type='channel'
        ).execute()
        
        channels = [{
            'id': item['snippet']['channelId'],
            'title': item['snippet']['title'],
            'thumbnail': item['snippet']['thumbnails']['default']['url']
        } for item in response['items']]
        
        return jsonify(channels)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/yandex/genres', methods=['GET'])
def api_yandex_genres():
    """Получение списка доступных жанров"""
    genres = [
        {'id': 'pop', 'name': 'Поп'},
        {'id': 'rock', 'name': 'Рок'},
        {'id': 'hiphop', 'name': 'Хип-хоп'},
        {'id': 'electronic', 'name': 'Электроника'},
        {'id': 'jazz', 'name': 'Джаз'},
        {'id': 'classical', 'name': 'Классика'},
        {'id': 'metal', 'name': 'Метал'},
        {'id': 'alternative', 'name': 'Альтернатива'},
        {'id': 'dance', 'name': 'Танцевальная'},
        {'id': 'blues', 'name': 'Блюз'}
    ]
    return jsonify(genres)


@app.route('/api/youtube/search/filtered', methods=['GET'])
def api_youtube_search_filtered():
    query = request.args.get('q')
    channel = request.args.get('channel')
    year = request.args.get('year')
    duration = request.args.get('duration')
    sort = request.args.get('sort', 'relevance')
    
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    results = ApiFunc.parse_youtube_videos_with_filters(
        query, 
        channel=channel, 
        year=year, 
        duration=duration, 
        sort=sort
    )
    return jsonify(results)


@app.route('/api/yandex/search/filtered', methods=['GET'])
def api_yandex_search_filtered():
    query = request.args.get('q')
    artist = request.args.get('artist')
    year = request.args.get('year')
    genre = request.args.get('genre')
    sort = request.args.get('sort', 'year')
    
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    results = ApiFunc.parse_yandex_tracks_with_filters(
        query, artist, year, genre, sort
    )
    return jsonify(results)

@app.route('/api/yandex/artist', methods=['GET'])
def api_yandex_artist_tracks():
    artist = request.args.get('q')
    if not artist:
        return jsonify({'error': 'Artist name is required'}), 400
    
    results = ApiFunc.search_yandex_artist_tracks(artist)
    print(results)
    return jsonify(results)

@app.route('/api/youtube/channel', methods=['GET'])
def api_youtube_channel_videos():
    channel = request.args.get('q')
    if not channel:
        return jsonify({'error': 'Channel name is required'}), 400
    
    results = ApiFunc.search_youtube_channel_videos(channel)
    return jsonify(results)

