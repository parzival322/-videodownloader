from flask import Flask, request, jsonify, render_template, send_from_directory
from api_functions import ApiFunc
import os
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Страница поиска YouTube
@app.route('/youtube')
def youtube_search_page():
    return render_template('youtube.html', active_tab='youtube')

# Страница поиска Яндекс.Музыки
@app.route('/yandex')
def yandex_search_page():
    return render_template('yandex.html', active_tab='yandex')

# Страница поиска VK
@app.route('/vk')
def vk_search_page():
    return render_template('vk.html', active_tab='vk')

@app.route('/api/download', methods=['POST'])
def api_download():
    # Принимаем данные в разных форматах
    if request.content_type == 'application/json':
        data = request.get_json()
    elif request.content_type in ['application/x-www-form-urlencoded', 'multipart/form-data']:
        data = request.form
    else:
        # Пытаемся автоматически определить формат
        try:
            data = request.get_json(force=True)
        except:
            data = request.form

    if not data:
        app.logger.error("No data received")
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    # Получаем параметры с учетом разных форматов запросов
    url = data.get('url')
    media_type = data.get('type', data.get('media_type', 'video'))
    format = data.get('format', 'mp4' if media_type == 'video' else 'mp3')

    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400

    try:
        # Определяем источник по URL
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

# @app.route('/api/vk/search', methods=['GET'])
# def api_vk_search():
#     query = request.args.get('q')
#     search_type = request.args.get('type')  # 'audio' или 'video'
    
#     if not query:
#         return jsonify({'error': 'Query parameter is required'}), 400
    
#     try:
#         if search_type == 'audio':
#             results = ApiFunc.search_vk_audio_v2(query)
#         elif search_type == 'video':
#             results = ApiFunc.search_vk_video_v2(query)
#         else:
#             return jsonify({'error': 'Invalid search type'}), 400
            
#         return jsonify({
#             'items': results,
#             'count': len(results)
#         })
        
#     except Exception as e:
#         app.logger.error(f"VK search error: {str(e)}")
#         return jsonify({
#             'error': 'Internal server error',
#             'details': str(e)
#         }), 500
    
# Для отдачи скачанных файлов
@app.route('/downloads/<path:filename>')
def download_file(filename):
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    yandex_dir = os.path.join(downloads_dir, "YandexMusic")
    
    # Проверяем разные возможные расположения файла
    for directory in [downloads_dir, yandex_dir]:
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            return send_from_directory(directory, filename, as_attachment=True)
    
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)