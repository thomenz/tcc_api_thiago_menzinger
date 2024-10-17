from fastapi import FastAPI, Body
import tinytuya
from fastapi.middleware.cors import CORSMiddleware
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@tool
def setLight(wich: int, set: bool) -> str:
    """ Set the light switch on or off

    Args:
        wich: The light switch to set, at the moment there's only 2 light switches available (1 and 2)
        set: The value to set the light switch to, True for on, False for off
    """
    d = tinytuya.Device('eb0f8f6acd25010e10pyzi', '192.168.1.8', ':_$w3s1bHJA`76ms', version=3.4)
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
    d = tinytuya.Device('eb0f8f6acd25010e10pyzi', '192.168.1.8', ':_$w3s1bHJA`76ms', version=3.4)
    data = d.status() 
    data = d.set_status(set, 1)
    data = d.set_status(set, 2)

@tool
def checkLights() -> str:
    """ Check the status of all the light switches
    """

    d = tinytuya.Device('eb0f8f6acd25010e10pyzi', '192.168.1.8', ':_$w3s1bHJA`76ms', version=3.4)
    data = d.status() 

    return f'Light 1 is {data["dps"]["1"]}, Light 2 is {data["dps"]["2"]}'

tools = [setLight, checkLights, setAllLights]

os.environ['OPENAI_API_KEY'] = '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'

llm = ChatOpenAI(model="gpt-4o-mini")

llm_with_tools = llm.bind_tools(tools)

@app.post("/")

def input_request(payload: dict = Body(...)):
    messages = [HumanMessage(payload['data'])]
    ai_msg = llm_with_tools.invoke(messages)
    messages.append(ai_msg)

    for tool_call in ai_msg.tool_calls:
        selected_tool = {"setLight": setLight, "checkLights": checkLights, "setAllLights": setAllLights}[tool_call["name"]]
        tool_msg = selected_tool.invoke(tool_call)
        messages.append(tool_msg)

    res = llm_with_tools.invoke(messages)
    return res.content