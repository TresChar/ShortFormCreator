import re
import textwrap
import os

from PIL import Image, ImageDraw, ImageFont
from rich.progress import track
from TTS.engine_wrapper import process_text

def draw_multiple_line_text(
    image, text, font, text_color, padding, wrap=50, transparent=False
) -> None:
    """
    Draw multiline text over given image
    """
    draw = ImageDraw.Draw(image)
    Fontperm = font.getsize(text)
    image_width, image_height = image.size
    lines = textwrap.wrap(text, width=wrap)
    y = (image_height / 2) - (((Fontperm[1] + (len(lines) * padding) / len(lines)) * len(lines)) / 2)
    for line in lines:
        line_width, line_height = font.getsize(line)
        if transparent:
            shadowcolor = "black"
            for i in range(1, 5):
                draw.text(
                    ((image_width - line_width) / 2 - i, y - i),
                    line,
                    font=font,
                    fill=shadowcolor,
                )
                draw.text(
                    ((image_width - line_width) / 2 + i, y - i),
                    line,
                    font=font,
                    fill=shadowcolor,
                )
                draw.text(
                    ((image_width - line_width) / 2 - i, y + i),
                    line,
                    font=font,
                    fill=shadowcolor,
                )
                draw.text(
                    ((image_width - line_width) / 2 + i, y + i),
                    line,
                    font=font,
                    fill=shadowcolor,
                )
        draw.text(((image_width - line_width) / 2, y), line, font=font, fill=text_color)
        y += line_height + padding


def imagemaker(theme, reddit_obj: dict, text_object: dict, txtclr, padding=5, transparent=False) -> None:
    """
    Render Images for video
    """
    title = process_text(reddit_obj["thread_title"], False)
    texts = reddit_obj["thread_post"]
    id = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])

    if transparent:
        font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), 100)
        tfont = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), 100)
    else:
        tfont = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), 100)  # for title
        font = ImageFont.truetype(os.path.join("fonts", "Roboto-Regular.ttf"), 100)
    size = (1920, 1080)
    
    image = Image.new("RGBA", size, theme)
    draw = ImageDraw.Draw(image)
    # for title
    draw_multiple_line_text(image, title, tfont, txtclr, padding, wrap=30, transparent=transparent)
    from utils import settings
    from typing import Dict, Final
    storymode: Final[bool] = settings.config["settings"]["storymode"]
    image.save(f"assets/temp/{id}/png/title.png")
    if(storymode and settings.config["settings"]["storymodemethod"] == 2):
        full_split_text = [""]
            
            
        #print(full_split_text)
        for idx, text in track(enumerate(texts), "Rendering Image"):
            #image = Image.new("RGBA", size, theme)
            text = process_text(text, False)
            word_count=0
            Fontperm = font.getsize(text)
            image_width, image_height = image.size
            split_text = text.split()
            full_split_text.append(split_text)
            #wordwrap = textwrap.wrap(text, width=30)
            #print(f"splittext={split_text}")
            for word in split_text:
                #print(f"word ={word}")
                word_width, word_height = font.getsize(word)
                text_object["words"].append(word)
                image = Image.new("RGBA", size, theme)
                drawword = ImageDraw.Draw(image)
                word_count+=1
                #draw_single_word(image, text, font, txtclr, padding, wrap=30, transparent=transparent)
                #word_width, word_height = font.getsize(word)
                y = (image_height/2) - (word_height)#not tested
                if transparent:
                    shadowcolor = "black"
                    draw.text(
                        ((image_width - word_width) / 2 , y ),
                        word,
                        font=font,
                        fill=shadowcolor,    
                    )
                
                drawword.text(((image_width - word_width) / 2, y), word, font=font, fill=txtclr)
                #moves along for multi words
                #y += word_height + padding
                #draw_multiple_line_text(image, word, font, txtclr, padding, wrap=30, transparent=transparent)
                #print(f"assets/temp/{id}/png/img{idx}-{word_count}.png")
                image.save(f"assets/temp/{id}/png/img{idx}-{word_count}.png")  
                #temp = [idx,word_count]
                #print(f"temp={temp}")
                #text_object["idx_and_word_count"].append(temp)
                  
        print("storymode=2")
        
        #add single word subtitles here
    else:
        for idx, text in track(enumerate(texts), "Rendering Image"):
            image = Image.new("RGBA", size, theme)
            text = process_text(text, False)
            #switched this to draw single word instead ofm draw multiple line text
            draw_single_word(image, text, font, txtclr, padding, wrap=30, transparent=transparent)
            #draw_multiple_line_text(image, text, font, txtclr, padding, wrap=30, transparent=transparent)
            image.save(f"assets/temp/{id}/png/img{idx}.png")       
        
def draw_single_word(
    image, text, font, text_color, padding, wrap=100, transparent=False
) -> None:
     
    draw = ImageDraw.Draw(image)
    Fontperm = font.getsize(text)
    image_width, image_height = image.size
    lines = textwrap.wrap(text, width=wrap)
    #lets take text in here instead so we can calculate in here and use as many var as poss
  
    line=1
    #y = (image_height / 2) - (((Fontperm[1] + (len(lines) * padding) / len(lines)) * len(lines)) / 2)
    for word in lines:
        
        word_width, word_height = font.getsize(word)
        y=(image_height/2) - (word_height)#not tested
        if transparent:
            shadowcolor = "black"
            draw.text(
                ((image_width - word_width) / 2 , y ),
                word,
                font=font,
                fill=shadowcolor,    
            )
              
        draw.text(((image_width - word_width) / 2, y), word, font=font, fill=text_color)
        y += word_height + padding