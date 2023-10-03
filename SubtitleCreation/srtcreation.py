from gtts import gTTS
import sounddevice as sd
import numpy as np
import re
import sys
from moviepy.editor import AudioFileClip

def create_srt_from_audio_mp3(mp3_name: str, sentences: str,reddit_object: dict):
    # Initialize variables
    audio_data = []
    sample_rate = 44100  # Adjust as needed
    reddit_id = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])
    # Step 1: Load the existing MP3 file
    # Use the provided mp3_name to load the MP3 file
    # For example:
    # mp3_file_path = f"path/to/your/mp3/{mp3_name}.mp3"
    # You should replace "path/to/your/mp3/" with the actual path to your MP3 files
    mp3_file_path = f".\\assets\\temp\\{reddit_id}\\{mp3_name}.mp3"
    print(mp3_file_path)
    audio_clip = AudioFileClip(mp3_file_path)

    duration = audio_clip.duration
    audio_data = []
    sample_rate = 44100  # Adjust as needed

    # Step 2: Play the audio and capture the spoken words and timings
    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        if any(indata):
            audio_data.append(np.copy(indata))

    with sd.InputStream(callback=callback, channels=1, dtype='int16', samplerate=sample_rate):
        # Calculate the duration based on the loaded MP3 file (you may need to obtain this information from the MP3 metadata)
        # Replace with the actual duration of the loaded MP3 in milliseconds
        sd.sleep(int(duration*1000))

    #audio_data = np.concatenate(audio_data)
    audio_data /= np.max(np.abs(audio_data))

    # Step 3: Generate SRT subtitles for each word
    print(sentences)
    for sentence in sentences:
        words = re.findall(r'\w+\'?\w*', sentence)
        print(words)

    #words = re.findall(r'\w+\'?\w*', sentence)#error here
    start_time = 0
    srt_content = ""

    for word in words:
        word_duration = int(len(word) * (duration / len(sentence)) * 100)  # Calculate word duration
        end_time = start_time + word_duration

        srt_content += f"{len(words) + 1}\n"  # Using len(words) as the sequence number
        srt_content += f"{start_time // 1000}:{start_time % 1000:03d} --> {end_time // 1000}:{end_time % 1000:03d}\n"
        srt_content += f"{word}\n\n"

        start_time = end_time
    
    # Write the subtitles to an SRT file with the same name as the MP3 file
    
    
    srt_file_path = f".\\assets\\temp\\{reddit_id}\\{mp3_name}.srt"
    print(srt_file_path)
    with open(srt_file_path, "w") as srt_file:
        srt_file.write(srt_content)


def create_srt_from_mp3(mp3_name: str, sentence: str,reddit_object: dict):
    # Initialize variables
    audio_data = []
    sample_rate = 44100  # Adjust as needed
    reddit_id = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])
    # Step 1: Load the existing MP3 file
    # Use the provided mp3_name to load the MP3 file
    # For example:
    # mp3_file_path = f"path/to/your/mp3/{mp3_name}.mp3"
    # You should replace "path/to/your/mp3/" with the actual path to your MP3 files
    mp3_file_path = f".\\assets\\temp\\{reddit_id}\\mp3\\{mp3_name}.mp3"
    
    audio_clip = AudioFileClip(mp3_file_path)

    duration = audio_clip.duration
    audio_data = []
    sample_rate = 44100  # Adjust as needed

    # Step 2: Play the audio and capture the spoken words and timings
    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        if any(indata):
            audio_data.append(np.copy(indata))

    with sd.InputStream(callback=callback, channels=1, dtype='int16', samplerate=sample_rate):
        # Calculate the duration based on the loaded MP3 file (you may need to obtain this information from the MP3 metadata)
        # Replace with the actual duration of the loaded MP3 in milliseconds
        sd.sleep(int(duration*1000))

    #audio_data = np.concatenate(audio_data)
    audio_data /= np.max(np.abs(audio_data))

    # Step 3: Generate SRT subtitles for each word
    words = re.findall(r'\w+\'?\w*', sentence)
    start_time = 0
    srt_content = ""

    for word in words:
        word_duration = int(len(word) * (duration / len(sentence)) * 100)  # Calculate word duration
        end_time = start_time + word_duration

        srt_content += f"{len(words) + 1}\n"  # Using len(words) as the sequence number
        srt_content += f"{start_time // 1000}:{start_time % 1000:03d} --> {end_time // 1000}:{end_time % 1000:03d}\n"
        srt_content += f"{word}\n\n"

        start_time = end_time
    
    # Write the subtitles to an SRT file with the same name as the MP3 file
    
    
    srt_file_path = f".\\assets\\temp\\{reddit_id}\\mp3\\{mp3_name}.srt"
    print(srt_file_path)
    with open(srt_file_path, "w") as srt_file:
        srt_file.write(srt_content)

if __name__ == "__main__":
    mp3_name = "sentence"  # Replace with the name of your MP3 file (without the .mp3 extension)
    sentence = "Hello, this is an example sentence."  # Replace with your sentence
    create_srt_from_mp3(mp3_name, sentence)
