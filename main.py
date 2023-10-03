#!/usr/bin/env python
import math
import sys
from os import name
from pathlib import Path
from subprocess import Popen
from typing import NoReturn

from tkinter import *
#from customtkinter import *

from prawcore import ResponseException
from utils.console import print_substep
from reddit.subreddit import get_subreddit_threads
from utils import settings
from utils.cleanup import cleanup
from utils.console import print_markdown, print_step
from utils.id import id
from utils.version import checkversion
from video_creation.background import (
    download_background_video,
    download_background_audio,
    chop_background,
    get_background_config,
)
from video_creation.final_video import make_final_video
from video_creation.screenshot_downloader import get_screenshots_of_reddit_posts
from video_creation.voices import save_text_to_mp3
from utils.ffmpeg_install import ffmpeg_install

from MyTikTokBot import MyTikTokBot
##UI
import customtkinter as CTk
from customtkinter import *


class MainForm(Toplevel):
    def __init__(self):
        
        super().__init__()
        #code coipied from tix needs to be adapted
        self.title("Main") 
        self.adjust_window_size()
        self.configure(background="#272537")
        self.frame = CTkFrame(self)
        self.frame.pack(pady=20,padx=60,fill="both",expand=True)
        self.label = CTkLabel(master=self.frame,text="Reddit TikTok Bot")
        #text_font=("Roboto",24)
        self.label.pack(pady=12,padx=10)
        #self.style = ttk.Style(self)
        #set_default_color_theme("dark")
            

        self.progressBar = CTkProgressBar(master = self.frame)
        self.progressBar.pack(pady = 12, padx = 10)
        #might need to set a value
        #self.mainloop()
        self.pre_run_checks_button = CTkButton(master = self.frame, text="Check everything is working",command=self.pre_run_checks)
        self.pre_run_checks_button.pack()
        self.run_bot_button = CTkButton(master = self.frame, text="Run Bot", command=self.run_bot)
        self.run_bot_button.pack()
    def pre_run_checks(self):
        if sys.version_info.major != 3 or sys.version_info.minor != 10:
            print("Hey! Congratulations, you've made it so far (which is pretty rare with no Python 3.10). Unfortunately, this program only works on Python 3.10. Please install Python 3.10 and try again.")
            sys.exit()
        ffmpeg_install()
        directory = Path().absolute()
        config = settings.check_toml(
            f"{directory}\\utils\\.config.template.toml", f"{directory}\\config.toml"
        )
        config is False and sys.exit()
            
        if (
            not settings.config["settings"]["tts"]["tiktok_sessionid"]
            or settings.config["settings"]["tts"]["tiktok_sessionid"] == ""
        ) and config["settings"]["tts"]["voice_choice"] == "tiktok":
            print_substep(
                "TikTok voice requires a sessionid! Check our documentation on how to obtain one.",
                "bold red",
            )
            sys.exit()
        try:
            if config["reddit"]["thread"]["post_id"]:
                for index, post_id in enumerate(
                    config["reddit"]["thread"]["post_id"].split("+")
                ):
                    index += 1
                    print_step(
                        f'on the {index}{("st" if index % 10 == 1 else ("nd" if index % 10 == 2 else ("rd" if index % 10 == 3 else "th")))} post of {len(config["reddit"]["thread"]["post_id"].split("+"))}'
                    )
                    main(post_id)
                    Popen("cls" if name == "nt" else "clear", shell=True).wait()
            elif config["settings"]["times_to_run"]:
                run_many(config["settings"]["times_to_run"])
            else:
                main()
        except KeyboardInterrupt:
            shutdown()
        except ResponseException:
            print_markdown("## Invalid credentials")
            print_markdown("Please check your credentials in the config.toml file")
            shutdown()
        except Exception as err:
            config["settings"]["tts"]["tiktok_sessionid"] = "REDACTED"
            config["settings"]["tts"]["elevenlabs_api_key"] = "REDACTED"
            print_step(
                f"Sorry, something went wrong with this version! Try again, and feel free to report this issue at GitHub or the Discord community.\n"
                f"Version: {__VERSION__} \n"
                f"Error: {err} \n"
                f'Config: {config["settings"]}'
            )
            raise err
    def adjust_window_size(self):
        ###TEMPP
        fullscreenvar = "off"
        if fullscreenvar=="on":
            self.attributes("-fullscreen", True)
        else:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            window_width = int(screen_width * 0.8)  # Adjust the window width as needed
            window_height = int(screen_height * 0.6)  # Adjust the window height as needed
            self.geometry(f"{window_width}x{window_height}")
    def run_bot(self):
        bot = MyTikTokBot()
        url = 'https://www.tiktok.com/login/phone-or-email/email'
        bot.execute_steps(url)  

__VERSION__ = "3.2.1"

checkversion(__VERSION__)

def text_object_def(text_object: dict):
     content = {}
     content["words"] = []
     content["idx"] = []     
     content["word count"] = []
     content["idx_and_word_count"] = []
     content["words_for_srt"]=[]
     return content

def main(POST_ID=None) -> None:
    global redditid, reddit_object, text_object
    text_object = ()
    reddit_object = get_subreddit_threads(POST_ID)
    text_object = text_object_def(text_object)
    redditid = id(reddit_object)
    length, number_of_comments, text_object = save_text_to_mp3(reddit_object,text_object)
    length = math.ceil(length)
    get_screenshots_of_reddit_posts(reddit_object, number_of_comments,text_object)
    bg_config = {
        "video": get_background_config("video"),
        "audio": get_background_config("audio"),
    }
    download_background_video(bg_config["video"])
    download_background_audio(bg_config["audio"])
    chop_background(bg_config, length, reddit_object)
    
    make_final_video(number_of_comments, length, reddit_object, bg_config,text_object)


def run_many(times) -> None:
    for x in range(1, times + 1):
        print_step(
            f'on the {x}{("th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th")[x % 10]} iteration of {times}'
        )  # correct 1st 2nd 3rd 4th 5th....
        main()
        Popen("cls" if name == "nt" else "clear", shell=True).wait()


def shutdown() -> NoReturn:
    if "redditid" in globals():
        print_markdown("## Clearing temp files")
        cleanup(redditid)
    
    print("Exiting...")
    sys.exit()


if __name__ == "__main__":
    ##main_form = MainForm()
    ##main_form.mainloop()
    count=0
    while(count==0):
        count+=1

        if sys.version_info.major != 3 or sys.version_info.minor != 10:
                print("Hey! Congratulations, you've made it so far (which is pretty rare with no Python 3.10). Unfortunately, this program only works on Python 3.10. Please install Python 3.10 and try again.")
                sys.exit()
        ffmpeg_install()
        directory = Path().absolute()
        config = settings.check_toml(
                f"{directory}\\utils\\.config.template.toml", f"{directory}\\config.toml"
            )
        config is False and sys.exit()
                
        if (
                not settings.config["settings"]["tts"]["tiktok_sessionid"]
                or settings.config["settings"]["tts"]["tiktok_sessionid"] == ""
            ) and config["settings"]["tts"]["voice_choice"] == "tiktok":
                print_substep(
                    "TikTok voice requires a sessionid! Check our documentation on how to obtain one.",
                    "bold red",
                )
                sys.exit()
        try:
                if config["reddit"]["thread"]["post_id"]:
                    for index, post_id in enumerate(
                        config["reddit"]["thread"]["post_id"].split("+")
                    ):
                        index += 1
                        print_step(
                            f'on the {index}{("st" if index % 10 == 1 else ("nd" if index % 10 == 2 else ("rd" if index % 10 == 3 else "th")))} post of {len(config["reddit"]["thread"]["post_id"].split("+"))}'
                        )
                        main(post_id)
                        Popen("cls" if name == "nt" else "clear", shell=True).wait()
                elif config["settings"]["times_to_run"]:
                    run_many(config["settings"]["times_to_run"])
                else:
                    main()
        except KeyboardInterrupt:
                shutdown()
        except ResponseException:
                print_markdown("## Invalid credentials")
                print_markdown("Please check your credentials in the config.toml file")
                shutdown()
        except Exception as err:
                config["settings"]["tts"]["tiktok_sessionid"] = "REDACTED"
                config["settings"]["tts"]["elevenlabs_api_key"] = "REDACTED"
                print_step(
                    f"Sorry, something went wrong with this version! Try again, and feel free to report this issue at GitHub or the Discord community.\n"
                    f"Version: {__VERSION__} \n"
                    f"Error: {err} \n"
                    f'Config: {config["settings"]}'
                )
                raise err
