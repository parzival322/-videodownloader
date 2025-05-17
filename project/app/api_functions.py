import requests
from googleapiclient.discovery import build
import os
from pathlib import Path
import yandex_music
import json
import time
import re
import random
import asyncio
from pytubefix import YouTube
from pytubefix.cli import on_progress
import threading
from dotenv import load_dotenv


class ApiFunc():

    @staticmethod
    def parse_youtube_videos_by_name(video_name):

        load_dotenv()
        api_key = os.getenv('YOUTUBE_API_KEY')

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

        load_dotenv()
        api_key = os.getenv('YOUTUBE_API_KEY')
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
        client = yandex_music.Client().init()

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
        client =yandex_music.Client().init()

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
    def download_media(url, format="mp4"):
        """Универсальный метод для скачивания медиа с YouTube и Яндекс.Музыки"""
        if 'yandex' in url.lower():
            return ApiFunc.download_yandex_track(url, format)
        else:
            return ApiFunc.download_youtube_media(url, format)

    @staticmethod
    def download_yandex_track(url, format="mp3"):
        """Скачивание трека из Яндекс.Музыки"""
        try:
            load_dotenv()
            access_token = os.getenv('YANDEX_MUSIC_TOKEN')

            # Инициализация клиента
            client = yandex_music.Client(access_token).init()
            
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
            download_dir = str(Path.home() / "Downloads")
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
            track_id = url.lstrip('https://music.yandex.ru/album/')
            track_place = track_id.find('/track')
            track_id = (track_id[track_place:track_id.find('?') if '?' in track_id else None]).lstrip('/track')
            print(track_id)
            return track_id
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
    def download_youtube_media(url, format='mp4'):
        BLOCKED = [line.rstrip().encode() for line in open('blacklist.txt', 'r', encoding='utf-8')]
        TASKS = []

        def sanitize_filename(filename):
            return re.sub(r'[<>:"/\\|?*]', '', filename)

        async def main(host, port):
            server = await asyncio.start_server(new_conn, host, port)
            await server.serve_forever()

        async def pipe(reader, writer):
            while writer.is_closing():
                try:
                    writer.write(await reader.read(1500))
                    await writer.drain()
                except:
                    break
            writer.close()

        async def new_conn(local_reader, local_writer):
            http_data = await local_reader.read(1500)
            try:
                type, target = http_data.split(b"\r\n")[0].split(b" ")[0:2]
                host, port = target.split(b":")
            except:
                local_writer.close()
                return
            
            if type != b"CONNECT":
                local_writer.close()
                return
            
            local_writer.write(b'HTTP/1.1 200 OK\n\n')
            await local_writer.drain()

            try:
                remote_reader, remote_writer = await asyncio.open_connection(host, port)
            except:
                local_writer.close()
                return
            
            if port == b'443':
                await fragemtn_data(local_reader, remote_writer)

            TASKS.append(asyncio.create_task(pipe(local_reader, remote_writer)))
            TASKS.append(asyncio.create_task(pipe(remote_reader, local_writer)))

        async def fragemtn_data(local_reader, remote_writer):
            head = await local_reader.read(5)
            data = await local_reader.read(1500)
            parts = []
            if all([data.find(site) == -1 for site in BLOCKED]):
                remote_writer.write(head + data)
                await remote_writer.drain()
                return
            while data:
                part_len = random.randint(1, len(data))
                parts.append(bytes.fromhex("1603") + bytes([random.randint(0, 255)]) + int(
                    part_len).to_bytes(2, byteorder='big') + data[0:part_len])
                data = data[part_len:]
            remote_writer.write(b''.join(parts))
            await remote_writer.drain()

        # Запуск прокси в отдельном потоке
        def run_proxy():
            asyncio.run(main(host='127.0.0.1', port=8881))

        proxy_thread = threading.Thread(target=run_proxy, daemon=True)
        proxy_thread.start()

        # Даем время на запуск прокси
        time.sleep(2)

        def combine(audio: str, video: str, output: str) -> None:
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(downloads_dir, exist_ok=True)  # Создаём папку, если её нет
            
            # Полный путь к итоговому файлу
            output_path = os.path.join(downloads_dir, output)

            if os.path.exists(output_path):
                os.remove(output_path)
            code = os.system(
                f'.\\ffmpeg\\bin\\ffmpeg.exe -i "{video}" -i "{audio}" -c copy "{output_path}"')
            
            if code == 0:
                os.remove(output)
                os.remove(output[:-3] + 'm4a')
                if os.path.exists(output_path):
                    return {'success':True, 'path': output_path}
                else:
                    return {'success':False, 'path':''}
            elif code != 0:
                raise SystemError(code)

        def download(url: str, format='mp3'):
            try:
                yt = YouTube(
                    proxies={"http": "http://127.0.0.1:8881",
                            "https": "http://127.0.0.1:8881"},
                    url=url,
                    on_progress_callback=on_progress,
                )
                video_stream = yt.streams.\
                    filter(type='video').\
                    order_by('resolution').\
                    desc().first()
                audio_stream = yt.streams.\
                    filter(mime_type='audio/mp4').\
                    order_by('filesize').\
                    desc().first()
                print('Information:')
                print("\tTitle:", yt.title)
                print("\tAuthor:", yt.author)
                print("\tDate:", yt.publish_date)
                print("\tResolution:", video_stream.resolution)
                print("\tViews:", yt.views)
                print("\tLength:", round(yt.length/60), "minutes")
                print("\tFilename of the video:", video_stream.default_filename)
                print("\tFilesize of the video:", round(
                    video_stream.filesize / 1000000), "MB")
                print('Download video...')
                if format == 'mp4':
                    video_stream.download()
                    print('\nDownload audio...')
                    audio_stream.download()
                    output_filename = sanitize_filename(f'{yt.title}.mp4')
                    result = combine(audio_stream.default_filename, video_stream.default_filename,
                        output_filename)
                    
                    if result['success'] == True:
                        return {'success':True, 'path':result['path']}
                    else:
                        return {'success':False, 'path':''}
                if format == 'mp3':
                    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                    os.makedirs(downloads_dir, exist_ok=True)  # Создаём папку, если её нет
                    output_filename = sanitize_filename(f'{yt.title}.mp3')
                    output_path = os.path.join(downloads_dir, output_filename)

                    temp_file = audio_stream.download(filename_prefix="temp_")
    
                    # Конвертируем в MP3 через ffmpeg
                    code = os.system(f'.\\ffmpeg\\bin\\ffmpeg.exe -i "{temp_file}" -codec:a libmp3lame -q:a 2 "{output_path}"')
                    
                    # Удаляем временный файл
                    os.remove(temp_file)
                    if code == 0:
                        if os.path.exists(output_path):
                            return {'success':True, 'path': output_path}
                        else:
                            return {'success':False, 'path':''}
                    else:
                        raise SystemError(code)
                    
                
            except Exception as e:
                print(f"Error downloading video: {e}")
                return {'success': False, 'path': '', 'error': str(e)}
        

        try:
            result = download(url, format)
            return result
        except Exception as e:
            print(f"Error: {e}")
            return result

    @staticmethod
    def get_youtube_trending_videos():
        load_dotenv()
        api_key = os.getenv('YOUTUBE_API_KEY')
        youtube = build('youtube', 'v3', developerKey=api_key)

        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            chart="mostPopular",
            regionCode="RU",
            maxResults=20
        )
        
        response = request.execute()

        trending_videos = []
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
            trending_videos.append(video_dct)

        return trending_videos


    @staticmethod
    def get_yandex_popular_tracks():
        """Получение популярных треков с Яндекс.Музыки"""
        try:
            client = yandex_music.Client().init()
            # Получаем чарт
            chart = client.chart('world').chart
            
            popular_tracks = []
            for track_short in chart.tracks[:20]:  # Берем топ 20 треков
                track = track_short.track
                track_info = {
                    "track_id": track.id,
                    "track_title": track.title,
                    "author": track.artists[0].name if track.artists else "Unknown",
                    "album": track.albums[0].title if track.albums else "",
                    "album_id": track.albums[0].id if track.albums else "",
                    "track_duration_ms": track.duration_ms,
                    "cover_uri": track.cover_uri,
                    "track_url": f"https://music.yandex.ru/album/{track.albums[0].id}/track/{track.id}" 
                            if track.albums else "#"
                }
                popular_tracks.append(track_info)
            
            return popular_tracks
        except Exception as e:
            print(f"Error getting popular tracks: {e}")
            return []

    @staticmethod
    def search_yandex_artist_tracks(artist_name):
        """Поиск треков по исполнителю (только треки этого исполнителя)"""
        try:
            client = yandex_music.Client().init()
            
            # Ищем точное совпадение имени исполнителя
            search_result = client.search(artist_name, type_='artist')
            
            if not search_result.artists or not search_result.artists.results:
                return []
                
            # Берем первого найденного исполнителя
            artist = search_result.artists.results[0]
            
            # Получаем популярные треки исполнителя
            tracks = []
            artist_tracks = client.artists_tracks(artist.id, page_size=50)
            
            for track_short in artist_tracks:
                try:
                    track = track_short.track if hasattr(track_short, 'track') else track_short
                    
                    track_info = {
                        "track_id": track.id,
                        "track_title": track.title,
                        "author": artist.name,
                        "album": track.albums[0].title if track.albums else "",
                        "album_id": track.albums[0].id if track.albums else "",
                        "track_duration_ms": track.duration_ms,
                        "cover_uri": track.cover_uri,
                        "track_url": f"https://music.yandex.ru/album/{track.albums[0].id}/track/{track.id}" 
                                if track.albums else "#"
                    }
                    tracks.append(track_info)
                except Exception as e:
                    print(f"Error processing track: {e}")
                    continue
            
            return tracks
            
        except Exception as e:
            print(f"Error searching artist tracks: {e}")
            return []
        
    @staticmethod
    def search_youtube_channel_videos(channel_name, query=None):
        """Поиск видео на канале по названию канала и запросу"""
        try:
            youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
            
            # Сначала ищем канал
            search_response = youtube.search().list(
                q=channel_name,
                part='snippet',
                type='channel',
                maxResults=1
            ).execute()
            
            if not search_response['items']:
                return []
                
            channel_id = search_response['items'][0]['id']['channelId']
            channel_title = search_response['items'][0]['snippet']['title']
            
            # Параметры для поиска видео
            params = {
                'channelId': channel_id,
                'part': 'snippet',
                'type': 'video',
                'maxResults': 50,
                'order': 'relevance'
            }
            
            if query:
                params['q'] = query
            
            # Ищем видео на канале
            search_response = youtube.search().list(**params).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response['items'] 
                        if item['id'].get('kind') == 'youtube#video']
            
            if not video_ids:
                return []
            
            # Получаем детали видео
            videos_response = youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(video_ids)
            ).execute()
            
            videos = []
            for item in videos_response['items']:
                # Проверяем соответствие запросу, если он был указан
                if query and query.lower() not in item['snippet']['title'].lower():
                    continue
                    
                video = {
                    "video_id": item['id'],
                    "video_title": item['snippet']['title'],
                    "channel_id": channel_id,
                    "channel_title": channel_title,
                    "video_duration": item['contentDetails']['duration'],
                    "video_publishtime": item['snippet']['publishedAt'],
                    "video_views": item['statistics']['viewCount'],
                    "video_thumbnails": item['snippet']['thumbnails'],
                    "video_url": f"https://www.youtube.com/watch?v={item['id']}"
                }
                videos.append(video)
            
            return videos
        except Exception as e:
            print(f"Error searching channel videos: {e}")
            return []
    

    @staticmethod
    def parse_youtube_videos_with_filters(query, channel=None, year=None, duration=None, sort='relevance'):
        """Поиск видео на YouTube с точной фильтрацией по каналу"""
        load_dotenv()
        api_key = os.getenv('YOUTUBE_API_KEY')
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        try:
            # Если указан канал, сначала находим его ID
            channel_id = None
            if channel:
                # Проверяем, не является ли channel уже ID канала (начинается с UC)
                if channel.startswith('UC'):
                    channel_id = channel
                else:
                    # Ищем канал по названию
                    search_response = youtube.search().list(
                        part='snippet',
                        q=channel,
                        type='channel',
                        maxResults=1
                    ).execute()
                    if search_response['items']:
                        channel_id = search_response['items'][0]['id']['channelId']

            # Параметры запроса
            params = {
                'part': 'snippet',
                'maxResults': 50,
                'q': query,
                'type': 'video',
                'order': sort
            }

            # Если нашли канал, добавляем фильтр
            if channel_id:
                params['channelId'] = channel_id

            # Поиск видео
            search_response = youtube.search().list(**params).execute()
            
            video_ids = []
            for item in search_response['items']:
                if item['id'].get('kind') == 'youtube#video':
                    video_ids.append(item['id']['videoId'])
            
            if not video_ids:
                return []

            # Получаем детальную информацию о видео
            videos_response = youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(video_ids)
            ).execute()

            parsed_videos = []
            for item in videos_response['items']:
                # Проверяем, что видео соответствует запросу (в названии)
                if query.lower() not in item['snippet']['title'].lower():
                    continue
                    
                # Проверяем длительность (если указана)
                if duration:
                    dur_str = item['contentDetails']['duration']
                    duration_sec = 0
                    if 'H' in dur_str:
                        duration_sec += int(dur_str.split('H')[0].split('T')[-1]) * 3600
                        dur_str = dur_str.split('H')[1]
                    if 'M' in dur_str:
                        duration_sec += int(dur_str.split('M')[0]) * 60
                        dur_str = dur_str.split('M')[1]
                    if 'S' in dur_str:
                        duration_sec += int(dur_str.split('S')[0])

                    if (duration == 'short' and duration_sec >= 240) or \
                    (duration == 'medium' and (duration_sec < 240 or duration_sec > 1200)) or \
                    (duration == 'long' and duration_sec <= 1200):
                        continue
                
                # Проверяем год (если указан)
                if year and year not in item['snippet']['publishedAt'][:4]:
                    continue

                video = {
                    "video_id": item['id'],
                    "video_title": item['snippet']['title'],
                    "channel_id": item['snippet']['channelId'],
                    "channel_title": item['snippet']['channelTitle'],
                    "video_duration": item['contentDetails']['duration'],
                    "video_publishtime": item['snippet']['publishedAt'],
                    "video_views": item['statistics'].get('viewCount', '0'),
                    "video_thumbnails": item['snippet']['thumbnails'],
                    "video_url": f"https://www.youtube.com/watch?v={item['id']}"
                }
                parsed_videos.append(video)

            # Сортировка результатов
            if sort == 'viewCount':
                parsed_videos.sort(key=lambda x: int(x['video_views']), reverse=True)
            elif sort == 'date':
                parsed_videos.sort(key=lambda x: x['video_publishtime'], reverse=True)
            elif sort == 'rating':
                parsed_videos.sort(key=lambda x: (
                    int(x.get('likeCount', 0)) / 
                    max(1, int(x.get('dislikeCount', 1)))
                ), reverse=True)

            return parsed_videos

        except Exception as e:
            print(f"Error searching YouTube videos: {e}")
            return []
    

    @staticmethod
    def parse_yandex_tracks_with_filters(query, artist=None, year=None, genre=None, sort='year'):
        """Поиск треков с фильтрами в Яндекс.Музыке"""
        try:
            client = yandex_music.Client().init()
            
            # Сначала ищем исполнителей (если указан артист)
            artist_ids = []
            if artist:
                artist_search = client.search(artist, type_='artist')
                if artist_search.artists:
                    artist_ids = [
                        a.id for a in artist_search.artists.results 
                        if artist.lower() in a.name.lower()
                    ]
            
            # Поиск треков
            search_result = client.search(text=query, nocorrect=False)
            
            if not search_result.tracks:
                return []
            
            tracks = []
            for track_short in search_result.tracks.results[:100]:  # Ограничиваем 100 результатами
                try:
                    track = track_short.track if hasattr(track_short, 'track') else track_short
                    
                    # Проверяем артиста (если указан)
                    if artist_ids and not any(a.id in artist_ids for a in track.artists):
                        continue
                        
                    # Проверяем год (если указан)
                    if year and track.albums and track.albums[0].year != int(year):
                        continue
                        
                    # Проверяем жанр (если указан)
                    if genre and track.albums and track.albums[0].genre.lower() != genre.lower():
                        continue
                    
                    main_artist = track.artists[0].name if track.artists else 'Unknown'
                    track_info = {
                        'track_id': track.id,
                        'track_title': track.title,
                        'author': main_artist,
                        'album': track.albums[0].title if track.albums else '',
                        'album_id': track.albums[0].id if track.albums else '',
                        'track_duration_ms': track.duration_ms,
                        'year': track.albums[0].year if track.albums and track.albums[0].year else None,
                        'genre': track.albums[0].genre if track.albums and track.albums[0].genre else None,
                        'cover_uri': track.cover_uri,
                        'track_url': f"https://music.yandex.ru/album/{track.albums[0].id}/track/{track.id}" 
                                if track.albums else "#",
                        'all_artists': ', '.join(a.name for a in track.artists) if track.artists else main_artist
                    }
                    tracks.append(track_info)
                except Exception as e:
                    print(f"Error processing track: {e}")
                    continue
            
            # Сортировка
            if sort == 'year':
                tracks.sort(key=lambda x: x['year'] if x['year'] else 0, reverse=True)
            elif sort == 'rating':
                tracks.sort(key=lambda x: x.get('likes', 0), reverse=True)
            elif sort == 'popularity':
                tracks.sort(key=lambda x: x.get('plays', 0), reverse=True)
            
            return tracks
            
        except Exception as e:
            print(f"Error searching Yandex Music: {e}")
            return []
    
