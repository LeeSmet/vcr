#!/usr/bin/env python3

from __future__ import unicode_literals, print_function
from snips_nlu.dataset import Dataset
import sounddevice as _
import speech_recognition as sr
from snips_nlu import SnipsNLUEngine
from snips_nlu.default_configs import CONFIG_EN
from typing import Any, Union
from jsonrpc2pyclient.rpcclient import RPCClient
from websockets.sync.client import connect
import click

_tfchain_mnemonic = ''
_stellar_secret = '' #TODO
_ssh_key = ''

class RPCWSClient(RPCClient):
    """A JSON-RPC WS Client."""

    def __init__(self, url: str):
        self._cl = connect(url)
        super(RPCWSClient, self).__init__()

    def disconnect(self):
        """Close the underlying websocket connection"""
        self._cl.close()

    def _send_and_get_json(self, request_json: str) -> Union[bytes, str]:
        self._cl.send(request_json)
        return self._cl.recv()

class CliInput():
    def __init__(self):
        pass

    def get_input(self):
        return input('>>>')

class MicrophoneInput():
    def __init__(self):
        # Setup audio input and recognizer
        self._r = sr.Recognizer()
        self._m = sr.Microphone()

        print("Calibrating microphone")
        with self._m as source: self._r.adjust_for_ambient_noise(source)
        print("Set minimum energy treshold to {}".format(self._r.energy_threshold))
        if self._r.energy_threshold < 300:
            self._r.energy_threshold = 300
            print("Set minimum energy treshold to {}".format(self._r.energy_threshold))

    def get_input(self):
        while(True):
            try:
                with self._m as source: audio = self._r.listen(source)
                print('captured input')
                # We just care about english for now, also use the small dataset instead of the base, which requires about 2GB of ram
                return self._r.recognize_whisper(audio, model='small.en', language='english')
            except sr.UnknownValueError:
                print("I did not understand what you are saying")



def _setup_engine():
    # Load NLU dataset and fit in model
    dataset = Dataset.from_yaml_files("en", ["training_dataset/model.yaml"])
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
            intent = VMProvision(intentMeta['slots'])
        case 'transferTft':
            intent = TftTransfer(intentMeta['slots'])
    return intent

# Class representing a TFT transfer intent
class TftTransfer():
    recipient = '' 
    amount = None
    chain = "stellar-mainnet"

    def __init__(self, slots: list[dict[str,Any]]) -> None:
        for slot in slots:
            match slot['slotName']:
                case 'recipient':
                    self.recipient = slot['value']['value']
                case 'amount':
                    self.amount = _parse_tft_amount(slot['value']['value'])
                case 'chain':
                    self.chain = slot['value']['value']

    def __str__(self) -> str:
        return "Transfer {} TFT to {} on chain {}".format(self.amount, self.recipient, self.chain)

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

    def mb(self):
        if self.value is None:
            raise Exception('memory not set')
        return self.value / 1_000_000

    def gb(self):
        if self.value is None:
            raise Exception('memory not set')
        return self.value / 1_000_000_000

# Class representing a VM Provision intent
class VMProvision():
    cpu = None
    ram = None
    disk = None
    image = 'Ubuntu 22.04'
    location = None
    nodeID = None
    farmID = None

    _image_path_map = {
        "Ubuntu 22.04": "https://hub.grid.tf/tf-official-vms/ubuntu-22.04-lts.flist",
        "Ubuntu 20.04": "https://hub.grid.tf/tf-official-vms/ubuntu-20.04-lts.flist",
        "Owncloud" :"https://hub.grid.tf/tf-official-apps/owncloud-10.9.1.flist",
        "presearch" :"https://hub.grid.tf/tf-official-apps/presearch-v2.3.flist",
    }

    def __init__(self, slots: list[Any]) -> None:
        for slot in slots:
            match slot['slotName']:
                case 'cpu':
                    self.cpu = _parse_cpu_amount(slot['value']['value'])
                case 'ram':
                    self.ram = _parse_datasize(slot['value']['value'])
                case 'disk':
                    self.disk = _parse_datasize(slot['value']['value'])
                case 'image':
                    self.image = slot['value']['value']
                case 'location':
                    self.location = slot['value']['value']
                case 'nodeID':
                    self.nodeID = _parse_nodeid(slot['value']['value'])
                case 'farmID':
                    self.farmID = _parse_farmid(slot['value']['value'])

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

    def image_url(self):
        if self.image is None:
            return None
        return self._image_path_map[self.image] if self.image in self._image_path_map else None

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

class W3CClient():
    _tfchain_address_book = {
        'Lee': '5HYRkLCPT6vVDDQPKrWgonBBagDuV5aneEarxR8Pr3LsvErq',
        'Kristof': '5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y', # Charlie well known account
        'Sabrina': '5HGjWAeFDfFCWPsjFQdVV2Msvz2XtMktvgocEZcCj68kUMaw', # Eve well known account
        'Jan': '5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy', # Dave well known account
    }

    _stellar_address_book = {
        'Lee': '',
        'Kristof': '', 
        'Sabrina': '', 
        'Jan': '', 
    }

    def __init__(self, url: str):
        self._cl = RPCWSClient(url)

    def handle(self, intent: VMProvision|TftTransfer):
        if isinstance(intent, TftTransfer):
            self.transfer_tft(intent)
            return
        if isinstance(intent, VMProvision):
            self.deploy_vm(intent)
            return
        raise Exception('unrecognized intent')


    def deploy_vm(self, vmp: VMProvision):
        self._load_grid_client("qa") # Hardcode deploy to qanet
        name = "vcr_poc"
        network = {"ip_range": "10.99.0.0/16", "add_wireguard_access": True}
        machines = {
                "name": "vm1",
                "node_id": vmp.nodeID if vmp.nodeID is not None else 0,
                "farm_id": vmp.farmID if vmp.farmID is not None else 0,
                "flist": vmp.image_url(),
                "entrypoint": "",
                "public_ip": True,
                "public_ip6": True,
                "planetary": True,
                "cpu": vmp.cpu,
                "memory": int(vmp.ram.mb()),
                "disks": [{
                    "size": int(vmp.disk.gb()),
                    "mountpoint": "/",
                }],
                "env_vars": {"SSH_KEY": _ssh_key},
                "description": "",
        }
        return self._cl.call("tfgrid.MachinesDeploy", [{"name":name, "network":network,"machines":[machines]}])

    def _load_grid_client(self, network: str):
        self._cl.call('tfgrid.Load', [{'network': network, 'mnemonic': _tfchain_mnemonic}])

    _stellar_networks = {"stellar-mainnet":  "public", "stellar-testnet": "testnet"}
    _tfchain_networks = {"TFChain-mainnet": "main", "TFChain-testnet": "test", "TFChain-qanet": "qa", "TFChain-devnet": "dev"}

    def transfer_tft(self, transfer: TftTransfer):
        if transfer.chain in self._stellar_networks:
            self._connect_stellar(self._stellar_networks[transfer.chain])
            self._transfer_stellar(transfer)
            return
        if transfer.chain in self._tfchain_networks:
            self._connect_tfchain(self._tfchain_networks[transfer.chain])
            self._transfer_tfchain(transfer)
            return
        raise Exception('unknown network')

    def _transfer_stellar(self, transfer: TftTransfer):
        if not transfer.recipient in self._stellar_address_book:
            raise Exception('unkown recipient')
        if transfer.amount is None:
            raise Exception('undefined transfer amount')
        return self._cl.call('stellar.Transfer', [{'amount': '{}'.format(transfer.amount), 'destination': self._stellar_address_book[transfer.recipient], 'memo': ''}])

    def _connect_stellar(self, network: str):
        self._cl.call('stellar.Load', [{'secret': _stellar_secret, 'network': network}])
        
    def _transfer_tfchain(self, transfer: TftTransfer):
        if not transfer.recipient in self._tfchain_address_book:
            raise Exception('unkown recipient')
        if transfer.amount is None:
            raise Exception('undefined transfer amount')
        return self._cl.call('tfchain.Transfer', [{'amount': transfer.amount * 10_000_000, 'destination': self._tfchain_address_book[transfer.recipient]}])

    def _connect_tfchain(self, network: str):
        self._cl.call('tfchain.Load', [{'network': network, 'mnemonic': _tfchain_mnemonic}])

@click.command()
@click.option('--cli', is_flag=True)
def main(cli=False):
    cl = W3CClient("ws://localhost:8080")

    nlu_engine = _setup_engine()

    if cli:
        input_engine = CliInput()
    else:
        input_engine = MicrophoneInput()

    try:
        while True:
            try:
                value = input_engine.get_input()
                print("Recognized input:\r\n{}".format(value))
                parsing = _extract_intent(value, nlu_engine)
                print(parsing)
                intent = parse_intent(parsing)
                print("Extract intent {}".format(intent))
                if intent is None:
                    print("could not parse an intent")
                    continue
                try:
                    ret = cl.handle(intent)
                    if ret is not None:
                        print(ret)
                except Exception as e:
                    print('got exception {}'.format(e))
                    continue
            except sr.UnknownValueError:
                print("I did not understand what you are saying")
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
