# Este código foi escrito por Thiago Menzinger
# E é parte do TCC do curso de Engenharia Mecatrônica na Unicesumar

# São realizadas as importações necessárias de bibliotecas externas
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

# Instancia a FastAPI 
app = FastAPI()

# Define as origens das quais vai aceitar requests
origins = [
    "http://localhost:3000",
]

# Endereço IP local do switch com as lampadas
lightsAdress = "192.168.1.8"

# Middleware que libera todas as origens e metodos ou headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define a chave de acesso da OPENAI, está em branco por questões de segurança, o ideal é utilizar variável de ambiente/segredos
os.environ['OPENAI_API_KEY'] = ''

# Definição das tools para que o Grande Modelo de Linguagem possa chama-lás
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

# Define o modelo de Embeddings, responsável por converter o texto em vetor para ser armazenado no banco de dados
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Inicia o cliente do banco de dados Qdrant que está rodando no container Docker da máquina
# ele também pode rodar localmente na memória: client = QdrantClient(":memory:")
# ou localmente no sistema de arquivos: client = QdrantClient(path="/tmp/langchain_qdrant")
client = QdrantClient(url="http://localhost:6333")

# Aqui é instanciado o banco de dados vetorial
vector_store = QdrantVectorStore(
    client=client,
    collection_name="tcc_collection",
    embedding=embeddings,
)

# Define o retriever, responsável por fazer a Geração Aumentada de Recuperação no banco de dados vetorial
retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 1})

# Cria-se uma ferramenta de busca no banco de dados vetorial para que o LLM a use quando necessário
retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_light_instructions",
    "Search and returns light instructions for turn on and off operations",
)

# Ferramentas listadas 
tools = [setLight, checkLights, setAllLights, retriever_tool]

# Instancia o modelo de linguagem e a capacidade de histórico de mensagens do LangGraph
memory = MemorySaver()
model = ChatOpenAI(model="gpt-4o-mini",temperature=0)
agent_executor = create_react_agent(model, tools, checkpointer=memory)

# Todo request do tipo POST no IP do servidor executa o que vem após:
@app.post("/")

def input_request(payload: dict = Body(...)):
    # O payload diz respeito ao corpo (body) do request
    query = payload['data']
    # Esta configuração torna possível a segmentação do chat da LLM para que sejam possíveis multiplos chats
    config = {"configurable": {"thread_id": "thomenz123"}}
    # Chama o agente de geração aumentada de recuperação e diz a ele quem ele é, e o que ele deve ou não fazer, além de dizer qual é o input do usuário, neste caso o payload
    for chunk in agent_executor.stream(
        {"messages": [SystemMessage(content='You are a helpful residential automation assistant, every time the user asks to turn on or off the lights, check the light operations first, and tell the rules to the user if you cannot turn on the ligths'),HumanMessage(content=query)]}, config
    ):
        # mostra no console do servidor os dados da resposta da requisição
        print(chunk)
        print("----")
    # retorna a mensagem do Grande de Modelo de Linguagem ao front-end
    return chunk['agent']['messages'][0].content
