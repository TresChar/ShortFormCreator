from gtts import gTTS
import sounddevice as sd
import numpy as np
import re
import sys

def creating_srt_file(
    number_of_clips: int,
    text_object: dict,
    mp3_name:str,
    sentence:str
      # Added audio_data parameter
):
    # Step 1: Convert the sentence to speech and save as an MP3 file
    sentence = "Hello, this is an example sentence and that."
    tts = gTTS(sentence)
    tts.save("sentence.mp3")
    #use the mp3 name and movie py to collect the already created mp3 file.
    # Initialize variables
    audio_data = []
    sample_rate = 44100  # Adjust as needed
    duration = len(tts.text)  # Calculate approximate duration based on text length
    word_timings = []


    # Play the audio and capture the spoken words and timings
    

    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        if any(indata):
            audio_data.append(np.copy(indata))

    with sd.InputStream(callback=callback, channels=1, dtype='int16', samplerate=sample_rate):
        sd.sleep(int(duration * 1000))


    #audio_data = np.concatenate`   (audio_data)
    audio_data /= np.max(np.abs(audio_data))

    # Step 3: Generate SRT subtitles for each word
    words = re.findall(r'\w+', sentence)
    start_time = 0
    srt_content = ""

    for word in words:
        word_duration = int(len(word) * (duration / len(sentence)) * 100)  # Calculate word duration
        end_time = start_time + word_duration

        srt_content += f"{len(word_timings) + 1}\n"
        srt_content += f"{start_time // 1000}:{start_time % 1000:03d} --> {end_time // 1000}:{end_time % 1000:03d}\n"
        srt_content += f"{word}\n\n"

        start_time = end_time
        word_timings.append(end_time)

    # Write the subtitles to an SRT file
    '''with open("output.srt", "w") as srt_file:
        srt_file.write(srt_content)'''
    # Save the SRT file in a specific directory with a custom filename
    srt_file_path = "ShortFormCreator\SubtitleCreation\srt_file.srt"
    with open(srt_file_path, "w") as srt_file:
        srt_file.write(srt_content)




""" def main(POST_ID=None) -> None:
    global redditid, reddit_object, text_object
    text_object=()
    text_object = text_object_def(text_object)
    creating_srt_file(number_of_clips=1, text_object=text_object)

def text_object_def(text_object: dict):
    content = {}
    content["words"] = []
    content["idx"] = []
    content["word count"] = []
    content["idx_and_word_count"] = []
    content["title"] = []
    content["text"] = []
    return content

if __name__ == "__main__":
    main() """
