import multiprocessing
import os
import re
from os.path import exists  # Needs to be imported specifically
from typing import Final
from typing import Tuple, Any, Dict
import json
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

import vosk
import sys
from pydub import AudioSegment
#from speech_recognition import *
from moviepy.editor import VideoClip, TextClip, CompositeVideoClip
import pysrt
from PIL import Image

from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.editor import AudioFileClip

import tempfile
import threading
import time
from tiktok_uploader.upload import upload_video
console = Console()
from speech_recognition import  *
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence



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





def name_normalize(name: str) -> str:
    name = re.sub(r'[?\\"%*:|<>]', "", name)
    name = re.sub(r"( [w,W]\s?\/\s?[o,O,0])", r" without", name)
    name = re.sub(r"( [w,W]\s?\/)", r" with", name)
    name = re.sub(r"(\d+)\s?\/\s?(\d+)", r"\1 of \2", name)
    name = re.sub(r"(\w+)\s?\/\s?(\w+)", r"\1 or \2", name)
    name = re.sub(r"\/", r"", name)

    lang = settings.config["reddit"]["thread"]["post_lang"]
    if lang:
        print_substep("Translating filename...")
        translated_name = translators.translate_text(name, translator="google", to_language=lang)
        return translated_name
    else:
        return name


def prepare_background(reddit_id: str, W: int, H: int) -> str:
    output_path = f"assets/temp/{reddit_id}/background_noaudio.mp4"
    output = (
        ffmpeg.input(f"assets/temp/{reddit_id}/background.mp4")
        .filter("crop", f"ih*({W}/{H})", "ih")
        .output(
            output_path,
            an=None,
            **{
                "c:v": "h264",
                "b:v": "20M",
                "b:a": "192k",
                "threads": multiprocessing.cpu_count(),
            },
        )
        .overwrite_output()
    )
    try:
        output.run(quiet=True)
    except ffmpeg.Error as e:
        print(e.stderr.decode("utf8"))
        print("error#005")
        #commented out to see error 20/09/23
        #exit(1)
    return output_path


def merge_background_audio(audio: ffmpeg, reddit_id: str):
    """Gather an audio and merge with assets/backgrounds/background.mp3
    Args:
        audio (ffmpeg): The TTS final audio but without background.
        reddit_id (str): The ID of subreddit
    """
    background_audio_volume = settings.config["settings"]["background"]["background_audio_volume"]
    if background_audio_volume == 0:
        return audio  # Return the original audio
    else:
        # sets volume to config
        bg_audio = ffmpeg.input(f"assets/temp/{reddit_id}/background.mp3").filter(
            "volume",
            background_audio_volume,
        )
        # Merges audio and background_audio
        merged_audio = ffmpeg.filter([audio, bg_audio], "amix", duration="longest")
        return merged_audio  # Return merged audio


def make_final_video(
    number_of_clips: int,
    length: int,
    reddit_obj: dict,
    background_config: Dict[str, Tuple],
    text_object:dict
):
    """Gathers audio clips, gathers all screenshots, stitches them together and saves the final video to assets/temp
    Args:
        number_of_clips (int): Index to end at when going through the screenshots'
        length (int): Length of the video
        reddit_obj (dict): The reddit object that contains the posts to read.
        background_config (Tuple[str, str, str, Any]): The background config to use.
    """
    # settings values
    W: Final[int] = int(settings.config["settings"]["resolution_w"])
    H: Final[int] = int(settings.config["settings"]["resolution_h"])

    opacity = settings.config["settings"]["opacity"]

    reddit_id = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])

    allowOnlyTTSFolder: bool = (
        settings.config["settings"]["background"]["enable_extra_audio"]
        and settings.config["settings"]["background"]["background_audio_volume"] != 0
    )

    print_step("Creating the final video 🎥")

    background_clip = ffmpeg.input(prepare_background(reddit_id, W=W, H=H))

    # Gather all audio clips
    audio_clips = list()
    if number_of_clips == 0 and settings.config["settings"]["storymode"] == "false":
        print(
            "No audio clips to gather. Please use a different TTS or post."
        )  # This is to fix the TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
        exit()
    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["storymodemethod"] == 0:
            audio_clips = [ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3")]
            audio_clips.insert(1, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/postaudio.mp3"))
        elif settings.config["settings"]["storymodemethod"] == 1:
            audio_clips = [
                ffmpeg.input(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")
                for i in track(range(number_of_clips + 1), "Collecting the audio files...")
            ]
            audio_clips.insert(0, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3")) 
        elif settings.config["settings"]["storymodemethod"] == 2:
            idx_and_word_count=text_object["idx_and_word_count"]
            audio_clips = [
                ffmpeg.input(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")
                for i in track(range(number_of_clips + 1), "Collecting the audio files...")
            ]
            audio_clips.insert(0, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3")) 
            audio_clips_no_title = [
                ffmpeg.input(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")
                for i in track(range(number_of_clips + 1), "Collecting the audio files...")
            ]
            ##setting the stuff from engine 
            #collecting 0 seconds
            
            #audio_clips = [ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3")]
                        
            # Assuming you have already defined 'reddit_id' and 'idx_and_word_count'
            #["v"].filter("minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=120'").filter("minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=120")
       

                # Create an ffmpeg input for the processed audio clip
                #audio_clip = ffmpeg.input(output_audio_path)
                #trying to do this in code below instread 21/09/23
                # Append the processed audio clip to the list
                #audio_clips.append(audio_clip)
            audio_clips_words = [
                ffmpeg.input(f"assets/temp/{reddit_id}/mp3/word{item[0]}-{item[1]}.mp3")
                             
                for item in track(idx_and_word_count, "Collecting the audio files...")
            ]
            

           

            filtered_audio_clips = []
            
          
          ##checkabove
            audio_clips_words.insert(0,ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3"))
            filtered_audio_clips.insert(0,ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3"))
            #audio_clips.insert(0,ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3"))
            # Now, 'audio_clips' contains all the audio clips with their correct durations
            '''audio_clips_list.append(audio_clips)


            for item in track(idx_and_word_count,"Collecting the audio files..."):
                
                print(f"assets/temp/{reddit_id}/mp3/word{item[0]}-{item[1]}.mp3")
                audio_clips.insert = [
                        ffmpeg.input(f"assets/temp/{reddit_id}/mp3/word{item[0]}-{item[1]}.mp3")
                    ]
                audio_clips_list.append(audio_clips)
                audio_clips = [
                    ffmpeg.input(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")
                    for i in track(range(number_of_clips + 1), "Collecting the audio files...")
                ]
            #testing it before loop
            audio_clips.insert(0, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3"))
            audio_clips_list.append(audio_clips)'''
   
    else:
        audio_clips = [
            ffmpeg.input(f"assets/temp/{reddit_id}/mp3/{i}.mp3") for i in range(number_of_clips)
        ]
        audio_clips.insert(0, ffmpeg.input(f"assets/temp/{reddit_id}/mp3/title.mp3"))

        audio_clips_durations = [
            float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/{i}.mp3")["format"]["duration"])
            for i in range(number_of_clips)
        ]
        audio_clips_durations.insert(
            0,
            float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/title.mp3")["format"]["duration"]),
        )
    #print(*audio_clips)
    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["storymodemethod"]==2:
            #audio_concat = ffmpeg.concat(*filtered_audio_clips, a=1, v=0)
            audio_concat = ffmpeg.concat(*audio_clips, a=1, v=0)
            audio_clips_no_title_concat = ffmpeg.concat(*audio_clips_no_title, a=1, v=0)
        else:
            audio_concat = ffmpeg.concat(*audio_clips, a=1, v=0)
    else:
            audio_concat = ffmpeg.concat(*audio_clips, a=1, v=0)
        
    print(f"audio_concat={audio_concat}")
    
    try:
        ffmpeg.output(
        audio_concat, f"assets/temp/{reddit_id}/audio.mp3", **{"b:a": "192k"}
    ).overwrite_output().run(quiet=True)
        
    except ffmpeg.Error as e:
        
        print(e.stderr.decode("utf8"))
        
        #print(e)
        print("stderr:", e.stderr)
        print("error001")
        exit(1)
    console.log(f"[bold green] Video Will Be: {length} Seconds Long")
    try:
        ffmpeg.output(
        audio_clips_no_title_concat, f"assets/temp/{reddit_id}/audio_without_title.mp3", **{"b:a": "192k"}
    ).overwrite_output().run(quiet=True)
        
    except ffmpeg.Error as e:
        
        print(e.stderr.decode("utf8"))
        
        #print(e)
        print("stderr:", e.stderr)
        print("error005")
        exit(1)
    console.log(f"[bold green] Audio w/o title Video Will Be: {length} Seconds Long")
    
    screenshot_width = int((W * 45) // 100)
    audio = ffmpeg.input(f"assets/temp/{reddit_id}/audio.mp3")
    final_audio = merge_background_audio(audio, reddit_id)

    word_image_clips = list()
    image_clips = list()
    image_clips.insert(
        0,
        ffmpeg.input(f"assets/temp/{reddit_id}/png/title.png")["v"].filter(
            "scale", screenshot_width, -1
        ),
    )
    word_image_clips.insert(
        0,
        ffmpeg.input(f"assets/temp/{reddit_id}/png/title.png")["v"].filter(
            "scale", screenshot_width, -1
        ),
    )
  
    current_time = 0
    if settings.config["settings"]["storymode"]:
        
        if settings.config["settings"]["storymodemethod"] == 0:
                audio_clips_durations = [
                float(
                    ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")["format"]["duration"]
                )
                for i in range(number_of_clips)
            ]
                audio_clips_durations.insert(
                        0,
                        float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/title.mp3")["format"]["duration"]),
                    )
                image_clips.insert(
                        1,
                        ffmpeg.input(f"assets/temp/{reddit_id}/png/story_content.png").filter(
                            "scale", screenshot_width, -1
                        ),
                    )
                background_clip = background_clip.overlay(
                        image_clips[0],
                        enable=f"between(t,{current_time},{current_time + audio_clips_durations[0]})",
                        x="(main_w-overlay_w)/2",
                        y="(main_h-overlay_h)/2",
                    )
                current_time += audio_clips_durations[0]
        elif settings.config["settings"]["storymodemethod"] == 1:
            audio_clips_durations = [
                float(
                    ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")["format"]["duration"]
                )
                for i in range(number_of_clips)
            ]
            audio_clips_durations.insert(
                0,
                float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/title.mp3")["format"]["duration"]),
            )
            for i in track(range(0, number_of_clips + 1), "Collecting the image files..."):
                image_clips.append(
                    ffmpeg.input(f"assets/temp/{reddit_id}/png/img{i}.png")["v"].filter(
                        "scale", screenshot_width, -1
                    )
                )
                background_clip = background_clip.overlay(
                    image_clips[i],
                    enable=f"between(t,{current_time},{current_time + audio_clips_durations[i]})",
                    x="(main_w-overlay_w)/2",
                    y="(main_h-overlay_h)/2",
                )
                #to check
                print(image_clips[i])
                print(image_clips)
                current_time += audio_clips_durations[i]
        elif settings.config["settings"]["storymodemethod"] == 2:
            audio_clips_durations = [
                float(
                    ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3")["format"]["duration"]
                )
                for i in range(number_of_clips)
            ]
            audio_clips_durations.insert(
                0,
                float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/title.mp3")["format"]["duration"]),
            )
            for item in idx_and_word_count:
                #count+=1   
                print(f"item={item}")
                temp= ffmpeg.input(f"assets/temp/{reddit_id}/png/img{item[0]}-{item[1]}.png")["v"].filter(
                        "scale", screenshot_width, -1)
                word_image_clips.append(temp
                                )
            try:
                word_durations = []
                word_durations.append(
                    
                float(ffmpeg.probe(f"assets/temp/{reddit_id}/mp3/title.mp3")["format"]["duration"])
                )
                print(word_durations)
                word_count2=0
                print(f"number of clips ={number_of_clips}")
            except ffmpeg.Error as e:
                print(f"Error: {e.stderr}") 
            try:
                from SubtitleCreation.srtcreation import create_srt_from_audio_mp3
                mp3_name_without = "audio_without_title"
                create_srt_from_audio_mp3(mp3_name=mp3_name_without,sentence=reddit_obj["thread_post"],reddit_object=reddit_obj)
                srt_file_full = f"assets/temp/{reddit_id}/audio_without_title.srt"
                word_durations, word_count2 = process_srt_as_text(file_path=srt_file_full,word_count2=word_count2,word_durations=word_durations)
            except Exception as e:
                print(f"create-srt-without{e}")
            
                
            try:
                for i in range(number_of_clips):
            
                    # Load your MP3 audio file
                    #mp3_audio_file = f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3"

                    # Load the corresponding SRT subtitle file
                    srt_file = f"assets/temp/{reddit_id}/mp3/postaudio-{i}.srt"
                    print(srt_file)
                    
                    
    
                    """ try:
                        word_durations, word_count2 = process_srt_as_text(file_path=srt_file,word_count2=word_count2,word_durations=word_durations)
                    except Exception as ex:
                        print(f"ex={ex}") """
            
        
                # Load your MP3 audio file
                #mp3_audio_file = f"assets/temp/{reddit_id}/mp3/postaudio-{i}.mp3"

                # Load the corresponding SRT subtitle file
                """ srt_file = f"assets/temp/{reddit_id}/audio.srt"
                print(srt_file)
                from SubtitleCreation.srtcreation import create_srt_from_mp3
                from TTS.engine_wrapper import process_text
                create_srt_from_mp3(f"audio", process_text(text),reddit_object=reddit_obj)

                try:
                    word_durations, word_count2 = process_srt_as_text(file_path=srt_file,word_count2=word_count2,word_durations=word_durations)
                except Exception as ex:
                    print(f"ex={ex}") """
                """  # Your code for processing the audio and subtitles goes here

                    # Calculate and store the total duration of each word, including preceding silence
                    try:
                        for segment in srt_file:
                            print(segment)
                            word_duration = len(segment) / 1000.0  # Convert from milliseconds to seconds
                            
                            word_durations.append(float(word_duration))
                            print(f"Sentence {i}, Word duration: {word_duration} seconds")
                            #check if missing a gap here
                            temp2 = word_duration
                            print(temp2)
                            word_count2 += 1
                        for segment in srt_file:
        # Calculate the word duration in seconds (assuming words are separated by spaces)
                            words = segment.text.split()
                            print(words)
                            word_duration = len(words) / 1000.0  # Convert from milliseconds to seconds
                            word_durations.append(word_duration)
                            word_count2+=1
                            print(f"Subtitle {segment.index}: Word duration: {word_duration} seconds")
                            
                            #word_count += len(words)
                    except Exception as e:
                        print(e)
                    # Print the total word count and word durations
                    print(f"Total Word Count: {word_count2}")
                    print(f"Word Durations: {word_durations}") """



            except Exception as e:
                print(f"Error6: {e}")
            print(word_durations)


            
            print(word_count2)
            for i in range(word_count2+1):
                print(i)
                
                
                background_clip = background_clip.overlay(
                    word_image_clips[i],
                    enable=f"between(t,{current_time},{current_time + word_durations[i]})",
                    x="(main_w-overlay_w)/2",
                    y="(main_h-overlay_h)/2",
                )
                
                #to check
                #print(image_clips[count])
                #print(image_clips)
                #print(f"audio_durations={audio_clips_durations[i]}")
                print(f"word_audio_durations={word_durations[i]}")
                #current_time += audio_clips_durations[i]
                current_time += word_durations[i] 
                
    else:
        for i in range(0, number_of_clips + 1):
            image_clips.append(
                ffmpeg.input(f"assets/temp/{reddit_id}/png/comment_{i}.png")["v"].filter(
                    "scale", screenshot_width, -1
                )
            )
            image_overlay = image_clips[i].filter("colorchannelmixer", aa=opacity)
            background_clip = background_clip.overlay(
                image_overlay,
                enable=f"between(t,{current_time},{current_time + audio_clips_durations[i]})",
                x="(main_w-overlay_w)/2",
                y="(main_h-overlay_h)/2",
            )
            current_time += audio_clips_durations[i]

    title = re.sub(r"[^\w\s-]", "", reddit_obj["thread_title"])
    print(f"title = {title}")
    idx = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])
    title_thumb = reddit_obj["thread_title"]

    filename = f"{name_normalize(title)[:251]}"
    print(f"#004filename ={filename}")
    subreddit = settings.config["reddit"]["thread"]["subreddit"]

    if not exists(f"./results/{subreddit}"):
        print_substep("The 'results' folder could not be found so it was automatically created.")
        os.makedirs(f"./results/{subreddit}")

    if not exists(f"./results/{subreddit}/OnlyTTS") and allowOnlyTTSFolder:
        print_substep("The 'OnlyTTS' folder could not be found so it was automatically created.")
        os.makedirs(f"./results/{subreddit}/OnlyTTS")

    # create a thumbnail for the video
    settingsbackground = settings.config["settings"]["background"]

    if settingsbackground["background_thumbnail"]:
        if not exists(f"./results/{subreddit}/thumbnails"):
            print_substep(
                "The 'results/thumbnails' folder could not be found so it was automatically created."
            )
            os.makedirs(f"./results/{subreddit}/thumbnails")
        # get the first file with the .png extension from assets/backgrounds and use it as a background for the thumbnail
        first_image = next(
            (file for file in os.listdir("assets/backgrounds") if file.endswith(".png")),
            None,
        )
        if first_image is None:
            print_substep("No png files found in assets/backgrounds", "red")

        else:
            font_family = settingsbackground["background_thumbnail_font_family"]
            font_size = settingsbackground["background_thumbnail_font_size"]
            font_color = settingsbackground["background_thumbnail_font_color"]
            thumbnail = Image.open(f"assets/backgrounds/{first_image}")
            width, height = thumbnail.size
            thumbnailSave = create_thumbnail(
                thumbnail,
                font_family,
                font_size,
                font_color,
                width,
                height,
                title_thumb,
            )
            thumbnailSave.save(f"./assets/temp/{reddit_id}/thumbnail.png")
            print_substep(f"Thumbnail - Building Thumbnail in assets/temp/{reddit_id}/thumbnail.png")

    text = f"Background by {background_config['video'][2]}"
    background_clip = ffmpeg.drawtext(
        background_clip,
        text=text,
        x=f"(w-text_w)",
        y=f"(h-text_h)",
        fontsize=5,
        fontcolor="White",
        fontfile=os.path.join("fonts", "Roboto-Regular.ttf"),
    )
    background_clip = background_clip.filter("scale", W, H)
    print_step("Rendering the video 🎥")
    from tqdm import tqdm

    pbar = tqdm(total=100, desc="Progress: ", bar_format="{l_bar}{bar}", unit=" %")

    def on_update_example(progress) -> None:
        status = round(progress * 100, 2)
        old_percentage = pbar.n
        pbar.update(status - old_percentage)

    defaultPath = f"results/{subreddit}"
    with ProgressFfmpeg(length, on_update_example) as progress:
        path = defaultPath + f"/{filename}"
        print_step(f"limiting path from : {path}")
        path = (
            path[:251] + ".mp4"
        )  # Prevent a error by limiting the path length, do not change this. starting at 251
        '''path = (
            path[:30] + ".mp4"
        )'''
        print_substep(f"Limted version : {path}")
        try:
            ffmpeg.output(
                background_clip,
                final_audio,
                path,
                f="mp4",
                **{
                    "c:v": "h264",
                    "b:v": "20M",
                    "b:a": "192k",
                    "threads": multiprocessing.cpu_count(),
                },
            ).overwrite_output().global_args("-progress", progress.output_file.name).run(
                quiet=True,
                #overwrite_output=True,
                capture_stdout=False,
                capture_stderr=False,
            )
        #except Exception as ex:
         #   print(ex)
        except FileNotFoundError as e:
            if e.winerror == 206:
                print(f"Error: {e}. Skipping file: {path}")
                  # Continue to the next iteration of the loop

        except ffmpeg.Error as e:
            print(e.stderr.decode("utf8"))
            #exit(1)
    old_percentage = pbar.n
    pbar.update(100 - old_percentage)
    if allowOnlyTTSFolder:
        path = defaultPath + f"/OnlyTTS/{filename}"
        path = (
            path[:251] + ".mp4"
        )  # Prevent a error by limiting the path length, do not change this.
        print_step("Rendering the Only TTS Video 🎥")
        with ProgressFfmpeg(length, on_update_example) as progress:
            try:
                ffmpeg.output(
                    background_clip,
                    audio,
                    path,
                    f="mp4",
                    **{
                        "c:v": "h264",
                        "b:v": "20M",
                        "b:a": "192k",
                        "threads": multiprocessing.cpu_count(),
                    },
                ).overwrite_output().global_args("-progress", progress.output_file.name).run(
                    quiet=True,
                    overwrite_output=True,
                    capture_stdout=False,
                    capture_stderr=False,
                )
            except ffmpeg.Error as e:
                print(e.stderr.decode("utf8"))
                exit(1)

        old_percentage = pbar.n
        pbar.update(100 - old_percentage)
    pbar.close()
    save_data(subreddit, filename + ".mp4", title, idx, background_config["video"][2])
    print_step("Removing temporary files 🗑")
    cleanups = cleanup(reddit_id)
    print_substep(f"Removed {cleanups} temporary files 🗑")
    print_step("Done! 🎉 The video is in the results folder 📁")
    url = 'https://www.tiktok.com/login/phone-or-email/email'
    BROWSERS = [
        'chrome',
        'safari',
        'chromium',
        'edge',
        'firefox'
        ]
    #browser=choice(BROWSERS)
    # Get the current file's absolute path
    current_file_path = os.path.abspath(__file__)

    # Get the directory containing the current file
    current_file_directory = os.path.dirname(current_file_path)

    # Check the operating system and act accordingly
    if os.name == 'posix':  # Unix/Linux/Mac or Windows
        parent_directory = os.path.dirname(current_file_directory)
    elif os.name == 'nt':   # Windows
        parent_directory = os.path.dirname(current_file_directory)
    else:
        parent_directory = None  # Handle other operating systems

    if parent_directory:
        # Define the 'results' folder and 'subreddit' folder
        results_folder = os.path.join(parent_directory, 'results')   
    else:
        print("Unsupported operating system")
    if parent_directory:
        print("Parent Directory:", parent_directory)
    else:
        print("Unsupported operating system")
    
    completedfile = os.path.join(results_folder,f"{subreddit}\\{filename}.mp4")
    #if(background_config['video'][2]=="Aki"|background_config['video'][2]=="bbswitzer"):##add credits in 2nd of list
    #upload_video(completedfile,description="Don't forget to comment your opinion!",cookies='cookiesa.txt',browser = 'chrome') 
    #else:
    #upload_video(completedfile,description=f"Don't forget to comment your opinion! Background by {background_config['video'][2]}",cookies='cookiesa.txt',browser = 'chrome') 
  


def remove_silence(input_audio_path, output_audio_path):
    # Define the FFmpeg command for silence removal
    ffmpeg_command = [
        "ffmpeg",
        "-i", input_audio_path,
        "-af", "silenceremove=1:0:-50dB:-1:0:-50dB",  # Silence removal filter
        output_audio_path,
    ]

    # Run FFmpeg to remove silence from the audio clip
    try:
        subprocess.run(ffmpeg_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing FFmpeg: {e}")
        # Handle the error as needed
def silence_removal_filter(input_audio, silence_duration=2.0):
    return (
        input_audio
        .filter("silenceremove", start_periods=1, start_duration=0, start_threshold=-50, d=silence_duration)
    )
def remove_silence_by_duration(input_audio_path, output_audio_path, silence_duration,item,text_object):
    audio_clip = AudioFileClip(input_audio_path)
    word_count = text_object["word count"]
    print(word_count)
    word_list  = text_object["words"]
    """ for i in range (word_count):
        print(i)
        
        word_list.append[text_object["words"][i]]
    #word = text_object["words"] """
    #for item in word_list:
    for item in word_list:
        word = item
    #set word to a value
    #maybe create the probe for each word and each sentence. and then input it on the words length. but play the sentence audio.
        characters = [char for char in word]
        print(characters)
    

    for char in characters:
        if char in ['.', ',', '/', '>']:
            print()
        else:
            start_time = silence_duration
            print(f"duration={audio_clip.duration}")
            print(f"start_time{start_time}")
            end_time = audio_clip.duration - silence_duration
            print(f"endtime={end_time}")
            # Use ffmpeg_extract_subclip to trim the audio
    ffmpeg_extract_subclip(input_audio_path, start_time, end_time, targetname=output_audio_path)

        
        # Trim silence from the beginning
    
def process_srt_as_text(file_path:str,word_count2:int,word_durations:[]):
    #word_durations = []
    

    with open(file_path, 'r') as srt_file:
        lines = srt_file.readlines()

    j = 0
    while j < len(lines):
        print(f"j={j}")
         
        length = lines[j].strip()
        start_end_time = lines[j + 1].strip()
        word = lines[j + 2].strip()
        print(f"start_end_time={start_end_time},length={length}word={word}")

        # Convert start_time and end_time to seconds

        start_time, end_time = start_end_time.split(" --> ")
        print(f"start_time={start_time}endtime={end_time}")
        start_time_seconds = float(start_time.replace(':', '.'))*10.0

        end_time_seconds = float(end_time.replace(':', '.'))*10.0
        duration_seconds = end_time_seconds - start_time_seconds
        print(f"start_time={start_time},end_time={end_time}start_time_seconds={start_time_seconds}end_time_seconds={end_time_seconds}duration_seconds={duration_seconds}")
        
        # Read the subtitle text
        
        # Print the subtitle and its duration
        print(f"Subtitle: {word}")
        print(f"Duration: {duration_seconds} seconds")
        

        # Append the duration to the word_durations list
        word_durations.append(float(duration_seconds))
        word_count2 += 1
        j +=3
        # Skip empty lines
        j += 1

    # Print the total word count and word durations
    print(f"Total Word Count: {word_count2}")
    print(f"Word Durations: {word_durations}")
    return word_durations, word_count2





