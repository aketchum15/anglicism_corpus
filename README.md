### German Anglicism Corpus


#### Set up
In order to install all the required packages first create a python virtual environment:
```
python3 -m venv .
```

Next, activate the virtual environment:
```
source bin/activate
```

Finally install the required packages:
```
pip install -r requirements.txt
```


##### Getting your api key
begin by following the first three steps in the section "before you start" at the link below:
https://developers.google.com/youtube/v3/getting-started

Next follow the steps in the section "Set up your project credentials" at the link below:
https://developers.google.com/youtube/v3/quickstart/python

Once you have downloaded you clients_secret.json file put move it to this folder and rename it to "secret.json"


#### Usage
In order to use the scraper provide it with a file that lists all the channels to be scraped:
```
python3 src/scraper.py [channel list]
```

Ex:
```
python3 src/scraper.py input/single.txt
```


For the analysis tool simply run the script as follows
```
python3 src/analysis.py
```

