from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from customtkinter import *
import tkinter as tk
from tkinter import ttk
import time

import logging

from tiktok_uploader.upload import upload_video




class MyTikTokBot:  
    def __init__(self):
        options = Options()
        self.driver = webdriver.Chrome(options=options)
        #Headless means it doesn't open??
        #options.add_argument("headless")
        options.add_experimental_option("detach", True)
        self.current_step= 0
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
        
    def set_video(self,url):
        '''
        videos = [
            {
                'video': 'video0.mp4',
                'description': 'Video 1 is about ...'
            },
            {
                'video': 'video1.mp4',
                'description': 'Video 2 is about ...'
            }
        ]'''
        FILENAME = "C:\\Users\\chart\\OneDrive\\Desktop\\Clips done\\Ice Skating - Tate.mp4"
        #auth = AuthBackend(cookies='cookiesa.txt')
        BROWSERS = [
            'chrome',
            'safari',
            'chromium',
            'edge',
            'firefox'
        ]
        #browser=choice(BROWSERS)
        upload_video(FILENAME,description="PLAIN BlACK VIDEO",cookies='cookiesa.txt',browser = 'chrome')
        
    def clear_text(self, element):
        print(element.get_attribute('value'))
        length = len(element.get_attribute('value'))
        print(length)
        element.send_keys(length * Keys.BACKSPACE)
    def move_to_next_step(self):
        self.current_step += 1

    def open_window(self, url):
        print(url)
        self.driver.get(url)
        self.driver.implicitly_wait(10)
        self.move_to_next_step()
        
    def find_sign_in_button(self):
        try:
            ticket_element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[class='sc-b8865be0-7 krWtzh'] span[class='sc-fdcd8351-1 gxREAk']")))
            ticket_element.click()
        except Exception as e:
            logging.error(f"Failed to find or click the sign-in button: {e}")
            return
        self.move_to_next_step()
        
    def sign_in(self):
        try:
            time.sleep(1.5)
            #need to make this dynamic maybe put a piece of closed source input that they can run called set up where they enter there email.
            #If we use classes we can make it so thety select from a menu system. One of the menu system being login and pass.It would have to maybe write this to a text file so it can be changed for each client.
            self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Email or username']").clear()
            print("email cleared")
            self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Email or username']").send_keys("tiktokautopost@proton.me")
            self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Password']").clear()
            self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Password']").send_keys("Tiktokautopost1738!")
            time.sleep(1.5)

            ticket_element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            ticket_element.click()

           
        except Exception as e:
            logging.error(f"Failed to fill in sign-in: {e}")
            return 
    

        self.move_to_next_step()
       
    def execute_steps(self, url):
        self.set_video(url)
        #self.open_window(url)
        #self.find_sign_in_button()
        #self.sign_in()
    
        #self.find_ticket_button()
        #self.keyword_selector()
        
        #self.checkout_page_1()
        #self.checkout_page_2()
        #self.buy()
  