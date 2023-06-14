#!/usr/bin/env python3

import speech_recognition as sr

for index, name in enumerate(sr.Microphone.list_microphone_names()):
    print("Microphone with name \"{1}\" found for `Microphone(device_index={0})`".format(index, name))

r = sr.Recognizer()
m = sr.Microphone()

try:
    print("Calibrating microphone")
    with m as source: r.adjust_for_ambient_noise(source)
    print("Set minimum energy treshold to {}".format(r.energy_threshold))
    while True:
        print("Say something")
        with m as source: audio = r.listen(source)
        print("Captured input")
        try:
            value = r.recognize_whisper(audio)
            print("Recognized input:\r\n{}".format(value))
        except sr.UnknownValueError:
            print("I did not understand what you are saying")
except KeyboardInterrupt:
    pass
