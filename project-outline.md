# Project outline

- Full Stack
- UI
- Framework
- Tech stack
- Backend
- Tech stack
- Data sources
- LLM Access

## **Tech Stack**
- Languages:
- [b,u] Python (Flask, Fastapi)
- C#
- Java
- C++
- [u] JS (TS)
- [x] Next.js (react)
- Shadcn and tailwind
- Tanstack start (react)
- Vue
- React
- Datasets
- Decide which ones to use.
- Weather (NOAA)
- Imagery (NASA)
- More if you can think of some

- Set up some sort of container that just curls the data and puts it into a DB
- Databases (Postgres) (ORMs)
- Relational
- Timeseries
- Vector (pgvector)
- LLM
- Gemini (free api key)
- Framework for interacting with LLM
- Langchain
- Genkit
- Crew
- Containers
- Docker
- Docker Compose
- Kubernetes (helm)

## **Minimum Viable Product**

- 1-2 data sources looking for weather
- 1 imagery source
- Gather data from past to show it works
- A bunch of fake publishing data (mock of the weather api sources)
```python
import pandas as pd
pd.read_csv("old_data.csv")
while True:
yield df[n:n+10]
sleep(10)
```
- Algorithm:
- [x] Take in the data (subscribe)
- Preprocessing and insert into DB (big csv)
- LLM looks at data and says "look here + coordinates and time", "nothing of note"
- Logs where to look
- Imagery is taken from those coordinates and time and model predicts fire or no fire
- Save these images to some report generator and save to file

## **Stages Past MVP** (Features)

- **Live UI**
- Actively show hot spots (like on a live map)
- Convincingly show that it works on live data
  
- **Larger scale past data**
- Validate with real past data
- In Provo, the weather leading up to the fire was like this (show some graphs), if we had this model running then would it have forseen the fire?
- How long before the fire does it flag the risk?
- How long until the first responders actually arrived, vs how when could we have notified them?
- How much would have been prevented had that happened.

- **IF you have extra time**
- Deployed live on an actual domain
- No longer hosted on your machine, but on some provider (cloudflare, vercel, netlify, oracle, ...)
- NATS, KAFKA


## **Tasks and Timeline**

- **Month 1**
- _Data sources_
- Weather
- Decide what kind of data you want (temperature, humidity, what else)
- Sources, (is it free? Can you get past data, can you find it in the areas you're interested in like Provo)
- Imagery (same as weather)
- Decide on tech stack
- UI, Backend language, container env, DB
- LLM Framework and API access
- Download and mock that API for subscribing to the data
- Feed LLM raw data and ask "What coordinates and time should I request imagery for?" then log the response
- (perhaps) Presented the idea, justification for why it's important, how you're going to approach this


# Matt:
- Server that gets realtime data from the weather
- Server that predicts on all models
- UI that displays the predictions of the various models
- UI that displays the maps
- Plans on how to integrate LLMs.


## Models to train:
- Random Forest (baseline)
- **XGBoost with class imbalances**
- Image fire detection
- Embedding models or Temporal Fusion Transformer

### Class of Problems:
- Anomoly detection
    - IEF
    - GANs
    - **Bayesian detection**


**Big training set (1 with class balanced, 1 with class imbalanced)**
**Less big test set**
*Could be derived from real time data*
*Knowing the tradeoffs between model choices*

```python
Class MyModel():
    def __init__(self, weights_path: str):
        pass
    def predict(self, data):
        pass
```


```python
# server running
from models import MyModel
model = MyModel(weights_path="weights.pth")

while true:
    for station in stations:
        data = get_data(station)
        prediction = model.predict(data)
        display(prediction)
```


This repo is going to have a front end, a back end, and then a models directory for various models. Inside the models directory as stated in the bottom of [project-outline.md](project-outline.md) there will be python classes that have ML models. The purpose of this is to display various potential hazardas fire areas. On the UI, in the front end directory, I want you to list out all the features that are currently there, then I'll add all the features I think it should have. Then we will create a plan for how to implement the ui completely. Lets do the same thing for the python server. Leave the models, they will be filled in later.

First thoughts:
UI
- show a list of the top 5 most likely fire areas currently from the backend, a list of location, timestamp, probability of fire.
- Then it shows a map of the globe zoomed to the locations that are in the list with dots symbolizing the location and color as probability of fire.
- The top should have a model selection where the results of that model are found. This should be a dropdown with the models names as the options.
- The UI should refresh every 10 seconds and transition smoothly to the new data.

Backend:
- The backend should have a route that returns the top `N` most likely fire areas currently.
- The backend should have a route that returns the satellite image for a given location.
- The backend should have a route that returns the weather data for a given location.
- The backend should have a route that returns the model predictions for a given location.
- There should be a postgres database that stores the weather data, the model predictions, and the satellite image filepaths.
  - the images should be mounted to the docker file system so that they can be accessed by the backend.
- There should be a background process that gets the weather data for all the weather stations in the list of stations I'll provide as a csv file every 10 seconds and stores it in the database.