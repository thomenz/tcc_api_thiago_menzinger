import os
from fastapi import FastAPI, Body
import tinytuya
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain.tools.retriever import create_retriever_tool


app = FastAPI()

origins = [
    "http://localhost:3000",
]

lightsAdress = "192.168.1.2"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.environ['OPENAI_API_KEY'] = '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'

@tool
def setLight(wich: int, set: bool) -> str:
    """ Set the light switch on or off

    Args:
        wich: The light switch to set, at the moment there's only 2 light switches available (1 and 2)
        set: The value to set the light switch to, True for on, False for off
    """
    d = tinytuya.Device('eb0f8f6acd25010e10pyzi', lightsAdress, ':_$w3s1bHJA`76ms', version=3.4)
    data = d.status() 
    
    if data['dps'][str(wich)] == False:
        data = d.set_status(True, wich)
        return f'Light {wich} is now on'
    elif data['dps'][str(wich)] == True:
        data = d.set_status(False, wich)
        return f'Light {wich} is now off'
    elif data['dps'][str(wich)] == None:
        return f'Light {wich} is not available'
    elif data['dps'][str(wich)] == set:
        return f'Light {wich} is already {set}'
    
@tool
def setAllLights(set: bool) -> str:
    """ Set all the light switches on or off

    Args:
        set: The value to set the light switches to, True for on, False for off
    """
    d = tinytuya.Device('eb0f8f6acd25010e10pyzi', lightsAdress, ':_$w3s1bHJA`76ms', version=3.4)
    data = d.status() 
    data = d.set_status(set, 1)
    data = d.set_status(set, 2)

@tool
def checkLights() -> str:
    """ Check the status of all the light switches
    """

    d = tinytuya.Device('eb0f8f6acd25010e10pyzi', lightsAdress, ':_$w3s1bHJA`76ms', version=3.4)
    data = d.status() 

    return f'Light 1 is {data["dps"]["1"]}, Light 2 is {data["dps"]["2"]}'

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

client = QdrantClient(url="http://localhost:6333")
vector_store = QdrantVectorStore(
    client=client,
    collection_name="tcc_collection",
    embedding=embeddings,
)

retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 1})

retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_light_instructions",
    "Search and returns light instructions for turn on and off operations",
)

tools = [setLight, checkLights, setAllLights, retriever_tool]

memory = MemorySaver()
model = ChatOpenAI(model="gpt-4o-mini",temperature=0)
agent_executor = create_react_agent(model, tools, checkpointer=memory)

@app.post("/")

def input_request(payload: dict = Body(...)):
    query = payload['data']
    config = {"configurable": {"thread_id": "thomenz123"}}
    for chunk in agent_executor.stream(
        {"messages": [SystemMessage(content='You are a helpful residential automation assistant, every time the user asks to turn on or off the lights, check the light operations first, and tell the rules to the user if you cannot turn on the ligths'),HumanMessage(content=query)]}, config
    ):
        print(chunk)
        print("----")

    return chunk['agent']['messages'][0].content
