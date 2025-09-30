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


