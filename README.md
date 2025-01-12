### German Anglicism Corpus


#### Set up
In order to install all the required packages first create a python virtual environment:
```
python3 -m venv .env
```

Next, activate the virtual environment:
```
source .env/bin/activate
```

Finally install the required packages:
```
pip install -r requirements.txt
python -m spacy download 'de_dep_news_trf'
```


##### Getting your api key
begin by following the first three steps in the section "before you start" at the link below:
https://developers.google.com/youtube/v3/getting-started

Next follow the steps in the section "Set up your project credentials" at the link below:
https://developers.google.com/youtube/v3/quickstart/python

Once you have downloaded you clients_secret.json file put move it to this folder and rename it to "secret.json"
```
.
├── .env
├── .git
├── .gitignore
├── input
├── output
├── pyrightconfig.json
├── README.md
├── requirements.txt
├── secret.json
├── src
└── test.py
```


#### Usage
In order to use the scraper provide it with a file that lists all the channels to be scraped:
```
python3 src/scraper.py [channel list]
```

Ex:
```
python3 src/scraper.py input/single.txt
```


The analysis tool can be run either to do the anglicism analysis using the command analyze, or to edit the scraped 
anglicism using the edit command.
```
# for analysis
python3 src/analysis.py analyze

# for editing
python3 src/analysis.py edit
```

edit mode loads the anglicism objects into a pandas dataframe for editing. Changes made to the words themselves or parts
of speech will be saved and the morphologies will be updated accordingly. Changes made to the morphologies will not be 
saved.

