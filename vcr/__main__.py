#!/usr/bin/env python3

from __future__ import unicode_literals, print_function
from snips_nlu.dataset import Dataset
import speech_recognition as sr
from snips_nlu import SnipsNLUEngine
from snips_nlu.default_configs import CONFIG_EN

for index, name in enumerate(sr.Microphone.list_microphone_names()):
    print("Microphone with name \"{1}\" found for `Microphone(device_index={0})`".format(index, name))

r = sr.Recognizer()
m = sr.Microphone()

# Load NLU dataset and fit in model
dataset = Dataset.from_yaml_files("en", ["training_dataset/model.yaml"])
print("Loaded dataset:\r\n\t{}".format(dataset.json))
nlu_engine = SnipsNLUEngine(config=CONFIG_EN)
nlu_engine = nlu_engine.fit(dataset)


try:
    print("Calibrating microphone")
    with m as source: r.adjust_for_ambient_noise(source)
    print("Set minimum energy treshold to {}".format(r.energy_threshold))
    if r.energy_threshold < 300:
        r.energy_threshold = 300
        print("Set minimum energy treshold to {}".format(r.energy_threshold))
    while True:
        print("Say something")
        with m as source: audio = r.listen(source)
        print("Captured input")
        try:
            # We just care about english for now, also use the small dataset instead of the base, which requires about 2GB of ram
            value = r.recognize_whisper(audio, model="small.en", language="english")
            print("Recognized input:\r\n{}".format(value))
            parsing = nlu_engine.parse(value)
            print(parsing)
        except sr.UnknownValueError:
            print("I did not understand what you are saying")
except KeyboardInterrupt:
    pass
