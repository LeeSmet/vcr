#!/usr/bin/env python3

from __future__ import unicode_literals, print_function
from snips_nlu.dataset import Dataset
import speech_recognition as sr
from snips_nlu import SnipsNLUEngine
from snips_nlu.default_configs import CONFIG_EN
from typing import Any

def main():
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print("Microphone with name \"{1}\" found for `Microphone(device_index={0})`".format(index, name))

    nlu_engine = _setup_engine()

    # Setup audio input and recognizer
    r = sr.Recognizer()
    m = sr.Microphone()

    try:
        print("Calibrating microphone")
        with m as source: r.adjust_for_ambient_noise(source)
        print("Set minimum energy treshold to {}".format(r.energy_threshold))
        if r.energy_threshold < 300:
            r.energy_threshold = 300
            print("Set minimum energy treshold to {}".format(r.energy_threshold))
        while True:
            print("Say something, energy treshold {}".format(r.energy_threshold))
            with m as source: audio = r.listen(source)
            print("Captured input")
            try:
                # We just care about english for now, also use the small dataset instead of the base, which requires about 2GB of ram
                value = r.recognize_whisper(audio, model="small.en", language="english")
                print("Recognized input:\r\n{}".format(value))
                parsing = _extract_intent(value, nlu_engine)
                print(parsing)
                intent = parse_intent(parsing)
                print("Extract intent {}".format(intent))
            except sr.UnknownValueError:
                print("I did not understand what you are saying")
    except KeyboardInterrupt:
        pass

def _setup_engine():
    # Load NLU dataset and fit in model
    dataset = Dataset.from_yaml_files("en", ["training_dataset/model.yaml"])
    print("Loaded dataset:\r\n\t{}".format(dataset.json))
    nlu_engine = SnipsNLUEngine(config=CONFIG_EN)
    nlu_engine = nlu_engine.fit(dataset)
    return nlu_engine

def _extract_intent(input: str, engine: SnipsNLUEngine):
    print("Analyzing input to figure out what you mean")
    return engine.parse(input)

def parse_intent(intentMeta):
    if intentMeta is None:
        return None
    intent = None
    match intentMeta['intent']['intentName']:
        case 'provisionVM':
            intent = VMProvision(intentMeta['intent']['slots'])
        case 'transferTFT':
            intent = TftTransfer(intentMeta['intent']['slots'])
    return intent

# Class representing a TFT transfer intent
class TftTransfer():
    recipient = None
    amount = None
    chain = "stellar-mainnet"

    def __init__(self, slots: list[Any]) -> None:
        for slot in slots:
            match slot.slotName:
                case 'recipient':
                    self.recipient = slot.value.value
                case 'amount':
                    self.amount = _parse_tft_amount(slot.value.value)
                case 'chain':
                    self.chain = slot.value.value

    def __str__(self) -> str:
        return "Transfer {} TFT to {} on chain {}".format(self.amount, self.recipient, self.chain)

# Class representing a VM Provision intent
class VMProvision():
    cpu = None
    ram = None
    disk = None
    image = 'Ubuntu 22.04'
    location = None
    nodeID = None
    farmID = None

    def __init__(self, slots: list[Any]) -> None:

        for slot in slots:
            match slot.slotName:
                case 'cpu':
                    self.cpu = _parse_cpu_amount(slot.value.value)
                case 'ram':
                    self.ram = _parse_datasize(slot.value.value)
                case 'disk':
                    self.disk = _parse_datasize(slot.value.value)
                case 'image':
                    self.image = slot.value.value
                case 'location':
                    self.location = slot.value.value
                case 'nodeID':
                    self.nodeID = _parse_nodeid(slot.value.value)
                case 'farmID':
                    self.farmID = _parse_farmid(slot.value.value)

    def __str__(self) -> str:
        if self.location is not None:
            loc = "in {}".format(self.location)
        elif self.nodeID is not None:
            loc = "on node {}".format(self.nodeID)
        elif self.farmID is not None:
            loc = "in farm {}".format(self.farmID)
        else:
            loc = "in unknown location"

        return "deploying VM running {} with {} VCPU, {} RAM, on a {} disk {}".format(self.image, self.cpu, self.ram, self.disk, loc)

class DataSize():
    value = None
    def __init__(self, val: int, metric: str) -> None:
        match metric.lower().strip(' '):
            case "mb":
                self.value = val * 1_000_000
            case "gb":
                self.value = val * 1_000_000_000
            case "tb":
                self.value = val * 1_000_000_000_000

    def __str__(self) -> str:
        if self.value is None:
            return "Unknown size"
        if self.value >= 1_000_000_000_000:
            return "{} TB".format(self.value / 1_000_000_000_000)
        elif self.value >= 1_000_000_000:
            return "{} GB".format(self.value / 1_000_000_000)
        else:
            return "{} MB".format(self.value / 1_000_000)



def _parse_cpu_amount(input: str):
    for p in input.split(' '):
        try:
            val = int(p)
            return val
        except:
            pass

def _parse_datasize(input: str):
    parts = input.split(' ')
    if len(parts) != 2:
        return None
    metric = _metric_from_str(parts[1])
    if metric is None:
        return None
    try:
        return DataSize(int(parts[0]), metric)
    except:
        pass

def _parse_tft_amount(input: str):
    for p in input.split(' '):
        try:
            val = int(p)
            return val
        except:
            pass
    return None

def _parse_nodeid(input: str):
    for p in input.split(' '):
        try:
            val = int(p)
            return val
        except:
            pass
    return None

def _parse_farmid(input: str):
    for p in input.split(' '):
        try:
            val = int(p)
            return val
        except:
            pass
    return None

def _metric_from_str(input: str):
    if input.lower() in ["mb", "megabyte", "megs", "meg"]:
        return "mb"
    if input.lower() in ["gb", "gigabyte", "gigs", "gig"]:
        return "gb"
    if input.lower() in ["tb", "terabyte", "tera"]:
        return "tb"

if __name__ == "__main__":
    main()
