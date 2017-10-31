#!/usr/bin/env python
from socket import *
import sys
import time
import string
import random
import unicodedata
from itertools import groupby
clientSocket = socket(AF_INET, SOCK_DGRAM)
addr = ("127.0.0.1", 12200)

face_gesture = ['A-I', 'C-D-G-K-N-S-TH', 'E', 'F-V', 'L', 'M', 'O', 'silent', 'U', 'W-Q']
letter_states = {}
for gest in face_gesture:
    if gest == 'silent':
        continue
    ltrs = gest.split('-')
    for ltr in ltrs:
        if ltr != '-':
            letter_states[ltr] = gest

soma_states = {
'normal-saccades': {'name': 'normal-saccades', 'magnitude': 1.0, 'rate': 1.0, 'ease_in': 0.0},
'normal': {'name': 'normal', 'magnitude': 1.0, 'rate': 1.0, 'ease_in': 0.0}, 
'breathing': {'name': 'breathing', 'magnitude': 1.0, 'rate': 1.0, 'ease_in': 0.0}
}

emotions = ['irritated', 'happy', 'recoil', 'surprised', 'sad', 'confused', 'worry', 'bored', 'engaged', 'amused', 'comprehending', 'afraid']

emotion_states = dict()
for emotion in emotions:
    emotion_states[emotion] = {emotion: {'magnitude': 0.9, 'duration': 2}}


def _print(string):
    sys.stdout.write(string)
    sys.stdout.flush()

def remove_diacritics(text):
    return unicodedata.normalize('NFKD', unicode(text)).encode('ASCII', 'ignore')

def speak_letter(letter):
    message = "queueViseme" + '\t' + letter_states.get(letter.upper(), '')
    clientSocket.sendto(message, addr)

def speak_word(word, letter_pause = 0.1):
    orig_word = word
    word = remove_diacritics(word)
    #uniq_word = [l[0] for l in groupby(word)]
    for oL, L in zip(orig_word, word):
        speak_letter(L)
        _print (oL)
        time.sleep(letter_pause)

def speak_text(text, word_pause = 0.1):
    words = text.split()
    for word in words:
        speak_word(word)
        time.sleep(word_pause)
        _print(" ") 

#commands.EvaAPI().setEmotionState("{'happy': {'magnitude': 0.9, 'duration': 10}}")
def set_emotion(state):
    message = "setEmotionState" + '\t' + str(state)
    clientSocket.sendto(message, addr)

def set_emotion_by_name(state_name):
    actual_state = emotion_states.get(state_name.lower().strip(), '')
    if not actual_state:
        return
    set_emotion(actual_state)

def random_set_emotion():
    emotion_nr = random.randint(0, len(emotion_states.keys()) - 1)
    emotion = emotion_states[emotion_states.keys()[emotion_nr]]
    if random.random() < 0.3:
        emotion['magnitude'] = random.random() 
    set_emotion(emotion)

def set_state(state):
    message = "setSomaStateString" + '\t' + str(state)
    clientSocket.sendto(message, addr)

def set_state_by_name(state_name):
    actual_state = soma_states.get(state.lower().strip(), '')
    if not actual_state:
        return
    set_state(actual_state)

def random_set_state():
    state_nr = random.randint(0, len(soma_states.keys()) - 1)
    state = soma_states[soma_states.keys()[state_nr]]
    if random.random() < 0.3:
        state['rate'] = random.random() * 10
        state['magnitude'] = random.random() * 10
    set_state(state)

def speak_self():
    with open('speak.py', 'r') as fin:
        text = fin.readlines()
    for line in text:
        speak_text(line)
        _print('\n')
    for line in text:
        speak_text(line)
        _print(' ')

def main():
    speak_self()

if __name__ == '__main__':
    main()