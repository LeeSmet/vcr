# vcr

Proof of concept for voice commands on TFGrid/3bot/...

## Installing

This was tested on python 3.11, though any python version since 3.8
should suffice. Installation platform was Arch linux, other platforms
should work though at this stage YMMV.

### Get code

Start by cloning the repo:

```bash
git clone https://github.com/LeeSmet/vcr
cd vcr
```

### Optional venv

You probably want to use a virtual env, though it is not required. If
you do want one:

```bash
python3 -m venv env
source ./env/bin/activate
```

### Install portaudio

Make sure you have the `portaudio` package installed (this is needed to
capture the microphone input).

Ubuntu: 

```bash
sudo apt-get install python-pyaudio python3-pyaudio
```

OSX:

```bash
brew install portaudio
```

For other platforms, check [the PyAudio website](https://people.csail.mit.edu/hubert/pyaudio/#downloads)

### Install python packages

Now install the python packages from the `requirements.txt` file

```bash
pip install -r requirements.txt
```

After this, you should be good to go

## Running

Running the code is done by 

```bash
python3 vcr/__main__.py
```

in the root of the repository. Alternatively the `--cli` flag can be used, in which case the program will run in a chat like mode
