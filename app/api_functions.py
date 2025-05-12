import requests
from googleapiclient.discovery import build
import subprocess
import os
from pathlib import Path
import yt_dlp
from yandex_music import Client
import json
import time
import re
from tqdm import tqdm
from urllib.parse import urlparse, parse_qs

class ApiFunc():

    @staticmethod
    def download_media(url, media_type="video", format="mp4", quality="best"):
        """
        Улучшенный метод скачивания с обходом ограничений YouTube
        """
        download_dir = str(Path.home() / "Downloads")
        ydl_opts = {
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'quiet': False,
            'retries': 3,
            'socket_timeout': 30,
            'force_ipv4': True,
            'no_check_certificate': True,
            'http_chunk_size': 10485760,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['config', 'webpage']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.youtube.com/',
            },
            'proxy': '',  # Можно добавить прокси при необходимости
        }

        # Альтернативные варианты форматов
        format_selectors = {
            'video': {
                'mp4': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]',
                'webm': 'bv*[ext=webm]+ba[ext=webm]/b[ext=webm]'
            },
            'audio': {
                'mp3': 'ba/b',
                'wav': 'ba/b'
            }
        }

        try:
            # Пробуем разные варианты форматов
            for attempt in range(3):
                try:
                    if media_type == "video":
                        ydl_opts['format'] = format_selectors['video'].get(format, 'bv*+ba/b')
                        if format == "mp4":
                            ydl_opts['merge_output_format'] = 'mp4'
                    else:
                        ydl_opts['format'] = format_selectors['audio'].get(format, 'ba/b')
                        if format == "mp3":
                            ydl_opts['postprocessors'] = [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '320',
                            }]
                        elif format == "wav":
                            ydl_opts['postprocessors'] = [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'wav',
                            }]

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)

                        if media_type == "audio":
                            filename = os.path.splitext(filename)[0] + f".{format}"

                        return filename

                except yt_dlp.DownloadError as e:
                    print(f"Попытка {attempt + 1} не удалась: {str(e)}")
                    if "HTTP Error 429" in str(e):
                        # Меняем User-Agent при блокировке
                        ydl_opts['http_headers'][
                            'User-Agent'] = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{91 + attempt}.0.4472.124 Safari/537.36'
                    time.sleep(5)  # Пауза между попытками
                    continue

        except Exception as e:
            print(f"Критическая ошибка: {type(e).__name__}: {e}")

        return None



    @staticmethod
    def parse_youtube_videos_by_name(video_name):
        api_key = 'AIzaSyCuAh9TGjixpvCANYYhQ0T3f-iCJAWAdGk'

        youtube = build('youtube', 'v3', developerKey=api_key)

        request = youtube.search().list(
            part="snippet",
            maxResults=50,
            q=video_name
        )

        response = request.execute()

        more_info_ids = ''
        for elem in response['items']:
            if elem['id'].get('kind') == 'youtube#video':
                more_info_ids = more_info_ids + elem['id'].get('videoId') + ','
        more_info_ids = more_info_ids[:-1]

        more_info_request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=more_info_ids,
            maxResults=50
        )

        more_info = more_info_request.execute()

        parsed_videos = []
        for elem in more_info['items']:
            video_dct = {
                "video_id": elem['id'],
                "video_title": elem['snippet'].get('title'),
                "channel_id": elem['snippet'].get('channelId'),
                "channel_title": elem['snippet'].get('channelTitle'),
                "video_duration": elem['contentDetails'].get('duration'),
                "video_publishtime": elem['snippet'].get('publishedAt'),
                "video_views": elem['statistics'].get('viewCount'),
                "video_thumbnails": elem['snippet'].get('thumbnails'),
                "video_url": f"https://www.youtube.com/watch?v={elem['id']}"
            }
            parsed_videos.append(video_dct)

        return parsed_videos

    @staticmethod
    def find_youtube_video_by_url(url):
        video_id = ''

        if not('&') in url:
            video_id = url[32:]
        else:
            first_ampersand = url.find('&')
            video_id = url[32:first_ampersand]

        api_key = 'AIzaSyCuAh9TGjixpvCANYYhQ0T3f-iCJAWAdGk'
        youtube = build('youtube', 'v3', developerKey=api_key)

        more_info_request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )

        response = more_info_request.execute()

        parsed_videos = []
        for elem in response['items']:
            video_dct = {
                "video_id": elem['id'],
                "video_title": elem['snippet'].get('title'),
                "channel_id": elem['snippet'].get('channelId'),
                "channel_title": elem['snippet'].get('channelTitle'),
                "video_duration": elem['contentDetails'].get('duration'),
                "video_publishtime": elem['snippet'].get('publishedAt'),
                "video_views": elem['statistics'].get('viewCount'),
                "video_thumbnails": elem['snippet'].get('thumbnails'),
                "video_url": f"https://www.youtube.com/watch?v={elem['id']}"
            }
            parsed_videos.append(video_dct)

        return parsed_videos

    @staticmethod
    def parse_yandex_tracks_by_name(name):
        client = Client().init()

        response = (client.search(name, type_='track')).to_json()

        response_data = json.loads(response)


        parsed_tracks = []

        for elem in response_data['tracks'].get('results'):
            new_dct = {
                'track_id': elem['id'],
                'album_id': elem['albums'][0].get('id'),
                'track_title': elem['title'],
                'author': elem['artists'][0].get('name'),
                'track_duration_ms': elem['duration_ms'],
                'cover_uri': elem['cover_uri'],
                'track_url': f'https://music.yandex.ru/album/{elem["albums"][0].get("id")}/track/{elem["id"]}'
            }
            parsed_tracks.append(new_dct)


        return parsed_tracks


    @staticmethod
    def find_yandex_music_track_by_url(url):
        client = Client().init()

        album_id = url.lstrip('https://music.yandex.ru/album/')
        track_place = album_id.find('/track')
        album_id = album_id[0:track_place]

        track_id = url.lstrip('https://music.yandex.ru/album/')
        track_place = track_id.find('/track')
        track_id = (track_id[track_place:track_id.find('?') if '?' in track_id else None]).lstrip('/track')

        try:
            track = client.tracks([f"{track_id}"])[0]  # Получаем трек по ID
            track_info = {
                "id": track.id,
                "title": track.title,
                "artists": [artist.name for artist in track.artists],
                "album": track.albums[0].title if track.albums else None,
                "duration": track.duration_ms // 1000,  # в секундах
                "cover_url": f"https://{track.cover_uri.replace('%%', '400x400')}" if track.cover_uri else None,
                "url": f"https://music.yandex.ru/album/{album_id}/track/{track_id}",
            }
            return track_info
        except Exception as e:
            print(f"Ошибка при получении трека: {e}")
            return None
 

    @staticmethod
    def search_vk_audio(query, count=30):
        access_token = '36d92ccd36d92ccd36d92ccd4735e82a9d336d936d92ccd5ef9cdfd4d84cf454655d72d'
        api_version = '5.199'


        def _make_api_request(method, params=None):
            """Базовый метод для API запросов"""
            if params is None:
                params = {}

            params.update({"access_token": access_token, "v": api_version})

            response = requests.get(f"https://api.vk.com/method/{method}", params=params)
            return response.json()

        """Поиск аудио по названию"""
        params = {
            "q": query,
            "count": count,
            "auto_complete": 1,
            "sort": 2,  # По популярности
        }

        result = _make_api_request("audio.search", params)
        return result.get("response", {}).get("items", [])


    @staticmethod
    def search_vk_video(query, count=30):
        access_token = '36d92ccd36d92ccd36d92ccd4735e82a9d336d936d92ccd5ef9cdfd4d84cf454655d72d'
        api_version = '5.199'


        def _make_api_request(method, params=None):
            if params is None:
                params = {}

            params.update({"access_token": access_token, "v": api_version})

            response = requests.get(f"https://api.vk.com/method/{method}", params=params)
            return response.json()

        params = {
            "q": query,
            "count": count,
            "sort": 2,  # По популярности
            "adult": 0,  # Без контента 18+
        }

        result = _make_api_request("video.search", params)
        return result.get("response", {}).get("items", [])        


    @staticmethod
    def get_vk_audio_by_id(owner_id, audio_id):
        access_token = '36d92ccd36d92ccd36d92ccd4735e82a9d336d936d92ccd5ef9cdfd4d84cf454655d72d'
        api_version = '5.199'

        def _make_api_request(method, params=None):
            if params is None:
                params = {}

            params.update({"access_token": access_token, "v": api_version})

            response = requests.get(f"https://api.vk.com/method/{method}", params=params)
            return response.json()

        params = {"audios": f"{owner_id}_{audio_id}"}

        result = _make_api_request("audio.getById", params)
        return result.get("response", [])[0] if result.get("response") else None

    @staticmethod
    def get_vk_video_by_id(owner_id, video_id):
        access_token = '36d92ccd36d92ccd36d92ccd4735e82a9d336d936d92ccd5ef9cdfd4d84cf454655d72d'
        api_version = '5.199'


        def _make_api_request(method, params=None):
            if params is None:
                params = {}

            params.update({"access_token": access_token, "v": api_version})

            response = requests.get(f"https://api.vk.com/method/{method}", params=params)
            return response.json()

        params = {"videos": f"{owner_id}_{video_id}"}

        result = _make_api_request("video.get", params)
        return result.get("response", {}).get("items", [None])[0]

    @staticmethod
    def download_tiktok_video(url):
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            domain = urlparse(url).netloc
            if 'tiktok.com' not in domain:
                raise ValueError("Это не ссылка на TikTok!")

            # Создаем папку для загрузок
            download_folder = os.path.join(os.path.expanduser("~"), "Desktop", "TikTok_Downloads")
            os.makedirs(download_folder, exist_ok=True)

            # Команда для скачивания через yt-dlp с конвертацией в AVC
            command = [
        'yt-dlp',
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        '--recode-video', 'mov',  # Перекодируем в MOV
        '--merge-output-format', 'mov',  # Объединяем в MOV
        '-o', os.path.join(download_folder, '%(title)s.%(ext)s'),
        '--no-warnings',
        url
    ]
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Видео успешно скачано в формате MP4 (AVC)!")
                for line in result.stderr.split('\n'):
                    if 'Destination:' in line:
                        file_path = line.split('Destination:')[-1].strip()
                        print(f"Файл сохранен: {file_path}")
                        return file_path
            else:
                print("Ошибка при скачивании:")
                print(result.stderr)
                
        except Exception as e:
            print(f"Произошла ошибка: {str(e)}")


    @staticmethod
    def search_vk_audio_v2(query, count=30):
        """Альтернативный метод поиска аудио"""
        try:
            print(f"\n=== Начинаем поиск аудио по запросу: '{query}' ===")
            
            access_token = '36d92ccd36d92ccd36d92ccd4735e82a9d336d936d92ccd5ef9cdfd4d84cf454655d72d'
            api_version = '5.199'
            
            params = {
                "q": query,
                "count": count,
                "access_token": access_token,
                "v": api_version
            }
            
            print("Параметры запроса:", params)
            
            response = requests.get("https://api.vk.com/method/audio.search", params=params)
            data = response.json()
            
            print("Полный ответ от API:", data)
            
            if 'error' in data:
                print(f"Ошибка API: {data['error']}")
                return []
                
            if 'response' not in data:
                print("Некорректный формат ответа - отсутствует 'response'")
                return []
                
            items = data['response'].get('items', [])
            print(f"Найдено {len(items)} аудиозаписей")
            
            results = []
            for item in items:
                try:
                    result = {
                        'id': item['id'],
                        'owner_id': item['owner_id'],
                        'title': item['title'],
                        'artist': item['artist'],
                        'duration': item['duration'],
                        'url': f"https://vk.com/audio{item['owner_id']}_{item['id']}"
                    }
                    results.append(result)
                    print(f"Добавлена аудиозапись: {result['title']} - {result['artist']}")
                except KeyError as e:
                    print(f"Ошибка в структуре аудиозаписи: отсутствует ключ {e}")
                    continue
                    
            return results
            
        except Exception as e:
            print(f"Исключение при поиске аудио: {str(e)}")
            return []

    @staticmethod
    def search_vk_video_v2(query, count=30):
        """Альтернативный метод поиска видео"""
        try:
            print(f"\n=== Начинаем поиск видео по запросу: '{query}' ===")
            
            access_token = '36d92ccd36d92ccd36d92ccd4735e82a9d336d936d92ccd5ef9cdfd4d84cf454655d72d'
            api_version = '5.199'
            
            params = {
                "q": query,
                "count": count,
                "access_token": access_token,
                "v": api_version,
                "adult": 0
            }
            
            print("Параметры запроса:", params)
            
            response = requests.get("https://api.vk.com/method/video.search", params=params)
            data = response.json()
            
            print("Полный ответ от API:", data)
            
            if 'error' in data:
                print(f"Ошибка API: {data['error']}")
                return []
                
            if 'response' not in data:
                print("Некорректный формат ответа - отсутствует 'response'")
                return []
                
            items = data['response'].get('items', [])
            print(f"Найдено {len(items)} видеозаписей")
            
            results = []
            for item in items:
                try:
                    # Получаем лучшее доступное изображение
                    image = item.get('photo_800') or item.get('photo_640') or item.get('photo_320') or ''
                    
                    result = {
                        'id': item['id'],
                        'owner_id': item['owner_id'],
                        'title': item['title'],
                        'duration': item['duration'],
                        'views': item.get('views', 0),
                        'image': image,
                        'url': f"https://vk.com/video{item['owner_id']}_{item['id']}"
                    }
                    results.append(result)
                    print(f"Добавлено видео: {result['title']} ({result['duration']} сек.)")
                except KeyError as e:
                    print(f"Ошибка в структуре видео: отсутствует ключ {e}")
                    continue
                    
            return results
            
        except Exception as e:
            print(f"Исключение при поиске видео: {str(e)}")
            return []
        

    @staticmethod
    def download_media(url, media_type="video", format="mp4"):
        """Универсальный метод для скачивания медиа с YouTube и Яндекс.Музыки"""
        if 'yandex' in url.lower():
            return ApiFunc.download_yandex_track(url, format)
        else:
            return ApiFunc.download_youtube_media(url, media_type, format)

    @staticmethod
    def download_yandex_track(url, format="mp3"):
        """Скачивание трека из Яндекс.Музыки"""
        try:
            # Инициализация клиента
            client = Client().init()
            
            # Парсим ID трека
            track_id = ApiFunc._parse_yandex_track_id(url)
            if not track_id:
                return {"success": False, "error": "Invalid Yandex Music URL"}

            # Получаем информацию о треке
            track = client.tracks([track_id])[0]
            if not track:
                return {"success": False, "error": "Track not found"}

            # Получаем ссылку на скачивание
            download_info = track.get_download_info()
            best_quality = max(
                [d for d in download_info if d.codec == 'mp3'],
                key=lambda x: x.bitrate_in_kbps
            )
            download_url = best_quality.get_direct_link()

            # Скачиваем файл
            download_dir = str(Path.home() / "Downloads" / "YandexMusic")
            os.makedirs(download_dir, exist_ok=True)
            
            filename = f"{track.title} - {track.artists[0].name}.{format}"
            filename = ApiFunc._sanitize_filename(filename)
            filepath = os.path.join(download_dir, filename)

            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return {"success": True, "path": filepath}
            else:
                return {"success": False, "error": f"Download failed: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _parse_yandex_track_id(url):
        """Парсинг ID трека из URL Яндекс.Музыки"""
        try:
            parts = url.split('/')
            track_part = [p for p in parts if p.startswith('track')]
            if not track_part:
                return None
            return track_part[0].replace('track', '')
        except:
            return None

    @staticmethod
    def _sanitize_filename(filename):
        """Очистка имени файла от недопустимых символов"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

    @staticmethod
    def download_youtube_media(url, media_type="video", format="mp4"):
        """Скачивание медиа с YouTube"""
        try:
            download_dir = str(Path.home() / "Downloads")
            os.makedirs(download_dir, exist_ok=True)

            ydl_opts = {
                'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
                'quiet': False,
                'retries': 3,
                'socket_timeout': 30,
                'force_ipv4': True,
                'no_check_certificate': True,
            }

            if media_type == "video":
                ydl_opts['format'] = f'bestvideo[ext={format}]+bestaudio[ext=m4a]/best[ext={format}]'
                ydl_opts['merge_output_format'] = format
            else:
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format,
                    'preferredquality': '320',
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if media_type == "audio":
                    filename = os.path.splitext(filename)[0] + f".{format}"

                return {"success": True, "path": filename}

        except Exception as e:
            return {"success": False, "error": str(e)}