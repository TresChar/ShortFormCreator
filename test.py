import multiprocessing
import os
import re
from os.path import exists  # Needs to be imported specifically
from typing import Final
from typing import Tuple, Any, Dict

import subprocess
import ffmpeg
import translators
from PIL import Image
from rich.console import Console
from rich.progress import track

from utils.cleanup import cleanup
from utils.console import print_step, print_substep
from utils.thumbnail import create_thumbnail
from utils.videos import save_data
from utils import settings



import tempfile
import threading
import time
from tiktok_uploader.upload import upload_video
console = Console()



class ProgressFfmpeg(threading.Thread):
    def __init__(self, vid_duration_seconds, progress_update_callback):
        threading.Thread.__init__(self, name="ProgressFfmpeg")
        self.stop_event = threading.Event()
        self.output_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.vid_duration_seconds = vid_duration_seconds
        self.progress_update_callback = progress_update_callback

    def run(self):
        while not self.stop_event.is_set():
            latest_progress = self.get_latest_ms_progress()
            if latest_progress is not None:
                completed_percent = latest_progress / self.vid_duration_seconds
                self.progress_update_callback(completed_percent)
            time.sleep(1)

    def get_latest_ms_progress(self):
        lines = self.output_file.readlines()

        if lines:
            for line in lines:
                if "out_time_ms" in line:
                    out_time_ms_str = line.split("=")[1].strip()
                    if out_time_ms_str.isnumeric():
                        return float(out_time_ms_str) / 1000000.0
                    else:
                        # Handle the case when "N/A" is encountered
                        return None
        return None

    def stop(self):
        self.stop_event.set()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()

            # Handle the error as needed

from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import AudioFileClip

def remove_silence_by_duration(input_audio_path, output_audio_path, silence_duration):
    audio_clip = AudioFileClip(input_audio_path)
    
    # Trim silence from the beginning
    start_time = silence_duration
    print(f"duration={audio_clip.duration}")
    print(f"start_time{start_time}")
    end_time = audio_clip.duration - silence_duration
    print(f"endtime={end_time}")
    # Use ffmpeg_extract_subclip to trim the audio
    ffmpeg_extract_subclip(input_audio_path, start_time, end_time, targetname=output_audio_path)

if __name__ == "__main__":
        
    idx_and_word_count = ([0,1],[0,2],[0,3],[0,4],[0,5],[0,6])
    for item in idx_and_word_count:
        print(item)
    audio_clips = [
                    ffmpeg.input(f"assets/temp/16olv0o/mp3/word{item[0]}-{item[1]}.mp3")                                
                    for item in track(idx_and_word_count, "Collecting the audio files...")
                ]
    print(audio_clips)
                
#assets\temp\16olv0o\mp3\word0-1.mp3
        
    filtered_audio_clips = []
    #   ######need to test in a new file with a set reddit id and a word. Test that i can actually remove silence from a word succesfully. If it works check how long and from what end of the word the silence needs reemoving.
    ##21/09/2023
    
    for item in track(idx_and_word_count):
        output_audio_path = (f"assets/temp/16olv0o/mp3/proccessed_word{item[0]}-{item[1]}.mp3")  # Set your desired output path
        remove_silence_by_duration(f"assets/temp/16olv0o/mp3/word{item[0]}-{item[1]}.mp3", output_audio_path, silence_duration=0.15)
        filtered_audio_clips.append(ffmpeg.input(output_audio_path))


    
    #audio_clips.insert(0,ffmpeg.input(f"assets/temp/160lv0o/mp3/title.mp3"))
    audio_concat = ffmpeg.concat(*filtered_audio_clips, a=1, v=0)
    print(f"audio_concat={audio_concat}")
    
    try:
        ffmpeg.output(
        audio_concat, f"assets/temp/16olv0o/audio.mp3", **{"b:a": "192k"}
    ).overwrite_output().run(quiet=True)
        
    except ffmpeg.Error as e:
        
        print(e.stderr.decode("utf8"))
        #exit(1)
        #print(e)
        print("stderr:", e.stderr)
        print("error001")
   





