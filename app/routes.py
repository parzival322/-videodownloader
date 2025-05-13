from flask import Flask, request, jsonify, render_template, send_from_directory
from api_functions import ApiFunc
import os
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

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

        result = ApiFunc.download_media(url, media_type, format)

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

if __name__ == '__main__':
    app.run(debug=True)