from tavily import TavilyClient
from langchain_core.tools import tool
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from datetime import datetime
import json
import os
absolute_path = os.path.abspath(__file__) # 현재 파일의 절대 경로 반환
current_path = os.path.dirname(absolute_path) # 현재 .py 파일이 있는 폴더 경로

# RAG를 위한 설정
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# OpenAI Embedding 설정
embedding = OpenAIEmbeddings(model='text-embedding-3-large')

# Chroma DB 저장 경로 설정
persist_directory = f"{current_path}/data/chroma_store"

# Chroma 객체 생성
vectorstore = Chroma(
    persist_directory=persist_directory,
    embedding_function=embedding
)

# Tavily API Key

from dotenv import load_dotenv
load_dotenv()
tavily_api_key = os.getenv('TAVILY_API_KEY')

@tool
def web_search(query: str):
    """
    주어진 query에 대해 웹검색을 하고, 결과를 반환한다.

    Args:
        query (str): 검색어

    Returns:
        dict: 검색 결과
    """
    client = TavilyClient(
        api_key=tavily_api_key
    )

    content = client.search(
        query, 
        search_depth="advanced",
        include_raw_content=True,
    )

    results = content["results"]

    for result in results:
        if result["raw_content"] is None:
            try:
                result["raw_content"] = load_web_page(result["url"])
            except Exception as e:
                print(f"Error loading page: {result['url']}")
                print(e)
                result["raw_content"] = result["content"]

    # 결과를 json 파일로 저장
    resources_json_path = f'{current_path}/data/resources_{datetime.now().strftime('%Y_%m%d_%H%M%S')}.json'
    with open(resources_json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
   
    return results, resources_json_path

def web_page_to_document(web_page):
    if len(web_page['raw_content']) > len(web_page['content']):
        page_content = web_page['raw_content']
    else:
        page_content = web_page['content']
    
    document = Document(
        page_content=page_content,
        metadata={
            'title': web_page['title'],
            'source': web_page['url']
        }
    )

    return document

def web_page_json_to_documents(json_file):
    with open(json_file, "r", encoding='utf-8') as f:
        resources = json.load(f)

    documents = []

    for web_page in resources:
        document = web_page_to_document(web_page)
        documents.append(document)

    return documents

def split_documents(documents, chunk_size=1000, chunk_overlap=100):
    print('Splitting documents...')
    print(f"{len(documents)}개의 문서를 {chunk_size}자 크기로 중첩 {chunk_overlap}자로 분할합니다.\n")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    splits = text_splitter.split_documents(documents)

    print(f"총 {len(splits)}개의 문서로 분할되었습니다.")
    return splits

def documents_to_chroma(documents, chunk_size=1000, chunk_overlap=100):
    print("Documents를 Chroma DB에 저장합니다.")

    # documents의 url 가져오기
    urls = [document.metadata['source'] for document in documents]

    # 이미 vectorstore에 저장된 urls 가져오기
    stored_metadatas = vectorstore._collection.get()['metadatas'] # vectorstore에 저장된 metadata 가져오기
    stored_web_urls = [metadata['source'] for metadata in stored_metadatas] # vectorstore에 저장된 url 가져오기

    # 새로운 urls만 남기기
    new_urls = set(urls) - set(stored_web_urls)

    # 새로운 urls에 대한 documents만 남기기
    new_documents = []

    for document in documents:
        if document.metadata['source'] in new_urls:
            new_documents.append(document)
            print(document.metadata)

    # 새로운 documents를 Chroma DB에 저장
    splits = split_documents(new_documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Chroma DB에 저장
    if splits:
        vectorstore.add_documents(splits)
    else:
        print("No new urls to process")

def add_web_pages_json_to_chroma(json_file, chunk_size=1000, chunk_overlap=100):
    documents = web_page_json_to_documents(json_file)
    documents_to_chroma(documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


@tool
def retrieve(query: str, top_k: int=5):
    """
    주어진 query에 대해 벡터 검색을 수행하고, 결과를 반환한다.
    """
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    retrieved_dcs = retriever.invoke(query)

    return retrieved_dcs

def load_web_page(url: str):
    loader = WebBaseLoader(url)

    content = loader.load()
    raw_content = content[0].page_content.strip()

    while '\n\n\n' in raw_content or '\t\t\t' in raw_content:
        raw_content = raw_content.replace('\n\n\n', '\n\n')
        raw_content = raw_content.replace('\t\t\t', '\t\t')
        
    return raw_content


if __name__ == "__main__":
    results, resources_json_path = web_search.invoke("HYBE 최근 논란")
    print(results)

    # # result = load_web_page("https://news.mt.co.kr/mtview.php?no=2024120402011362298")
    # # print(result)

    # documents = web_page_json_to_documents(f'{current_path}/data/resources_2024_1210_000142.json')
    
    # splits = split_documents(documents)

    # add_web_pages_json_to_chroma(f'{current_path}/data/resources_2024_1210_000142.json')

    # retrieved_docs = retrieve.invoke({"query": "HYBE 성공원인"})
    # print(retrieved_docs)