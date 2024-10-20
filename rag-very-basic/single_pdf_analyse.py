import os
import sys
import json
import re
from datetime import datetime
import pandas as pd
import pdfplumber
import openai
from tqdm import tqdm
from openai.embeddings_utils import get_embedding, cosine_similarity

# 运行环境初始化
os.environ["http_proxy"] = "http://127.0.0.1:1088"
os.environ["https_proxy"] = "http://127.0.0.1:1088"

openai.organization = "org-your_org"
openai.api_key = "sk-your_api_key"

full_report = ""

def search_embeddings(df, query, n=3, pprint=True):
    # Get embeddings for query and all text
    query_embedding = get_embedding(
        query,
        engine="text-embedding-ada-002"
    )
    df["similarity"] = df.embeddings.apply(lambda x: cosine_similarity(x, query_embedding)) # Calculate cosine similarity

    results = df.sort_values("similarity", ascending=False, ignore_index=True) # Sort by similarity
    results = results.head(n)
    global sources
    sources = []
    for i in range(n):
        sources.append({'Page '+str(results.iloc[i]['page']): results.iloc[i]['text'][:150]+'...'}) # Get top n results
    return results.head(n)

def create_prompt(df, user_input, strategy=None):
    # Create prompt
    result = search_embeddings(df, user_input) # Get top n results
    if strategy == "paper":
        prompt = """You are a large language model whose expertise is reading and summarizing scientific papers.
        You are given a query and a series of text embeddings from a paper in order of their cosine similarity to the query.
        You must take the given embeddings and return a very detailed summary of the paper that answers the query.
            Given the question: """+ user_input + """

            and the following embeddings as data: 

            1.""" + str(result.iloc[0]['text']) + """
            2.""" + str(result.iloc[1]['text']) + """

            Return a concise and accurate answer:"""
    elif strategy == "handbook":
        prompt = """You are a large language model whose expertise is reading and summarizing financial handbook.
        You are given a query and a series of text embeddings from a handbook in order of their cosine similarity to the query.
        You must take the given embeddings and return a very detailed answer in Chinese of the handbook that answers the query.
        If not necessary, your answer please use the original text as much as possible.
        You should also ensure that your response is written in clear and concise Chinese, using appropriate grammar and vocabulary.  
        Additionally, your response should focus on answering the specific query provided..
            Given the question: """+ user_input + """
            and the following embeddings as data: 

            1.""" + str(result.iloc[0]['text']) + """
            2.""" + str(result.iloc[1]['text']) + """

            Return a concise and accurate answer:"""
    elif strategy == "contract":
        prompt = """As a large language model specializing in reading and summarizing, your task is to read a query and a sequence of text inputs sorted by their cosine similarity to the query.
         Your goal is to provide a Chinese answer to the query using the given padding. If possible, please use the original text of your answer. 
         Please ensure that your response adheres to the terms of the agreement. Your response should focus on addressing the specific query provided, 
         providing relevant information and details based on the input texts' content. You should also strive for clarity and conciseness in your response, 
         summarizing key points while maintaining accuracy and relevance. Please note that you should prioritize understanding the context and meaning 
         behind both the query and input texts before generating a response.
            Given the question: """+ user_input + """
            and the following embeddings as data: 

            1.""" + str(result.iloc[0]['text']) + """
            2.""" + str(result.iloc[1]['text']) + """

            Return a concise and accurate answer:"""
    else:
        prompt = """As a language model specialized in reading and summarizing documents,your task is to provide a concise answer in Chinese based on a given query and a series of text embeddings from the document.The embeddings are provided in order of their cosine similarity to the query. Your response should use as much original text as possible.Your answer should be highly concise and accurate, providing relevant information that directly answers the query.You should ensure that your response is written in clear and concise Chinese, using appropriate grammar and vocabulary.Please note that you must use the provided text embeddings to generate your response, which means you will need to understand how they relate to the original document.Your response should focus on answering the specific query provided.Given the question: """+ user_input + """ and the following embeddings as data: 1.""" + str(result.iloc[0]['text']) + """2.""" + str(result.iloc[1]['text'])
    logger.info('Done creating prompt')
    return prompt

def extract_pdf_contents(pdf_path):
    # pdf文档输入
    file_name_prefix = pdf_path[:-4]
    pdf = pdfplumber.open(pdf_path)
    print('starting...')

    paper_text = []
    pre_read_content = ""

    with pdfplumber.open(pdf_path) as pdf:
        number_of_pages = len(pdf.pages)
        full_report = "{}分析文档{}，总页数{}\n\n".format(full_report, pdf_path, number_of_pages)
    
        # 对每一页的文本进行处理
        for i in range(len(pdf.pages)):
            if i <= 10 and len(pre_read_content) < 3000:
                pre_read_content = '{}{}'.format(pre_read_content, pdf.pages[i].extract_text()) # 读取前10页的内容
            else:
                pre_read_content = pre_read_content[0:3000]
            page = pdf.pages[i]
            words = page.extract_words(extra_attrs=['size'])
            blob_font_size = None
            blob_text = ''
            processed_text = []

            for word in words:
                if word['size'] == blob_font_size:
                    blob_text += f" {word['text']}"
                    if len(blob_text) >= 2000: #这个数值控制的是一个段落可能最小的长度
                        processed_text.append({
                            'fontsize': blob_font_size,
                            'text': re.sub(r'\.{2,}', ' ', blob_text),
                            'page': i
                        })
                        blob_font_size = None
                        blob_text = ''
                else:
                    if blob_font_size is not None and len(blob_text) >= 1:
                        processed_text.append({
                            'fontsize': blob_font_size,
                            'text': re.sub(r'\.{2,}', ' ', blob_text),
                            'page': i
                        })
                    blob_font_size = word['size']
                    blob_text = word['text']
                paper_text += processed_text
    return paper_text, pre_read_content

def generate_embeddings(df, file_name_prefix):
    # 生成embeddings
    print('embeddings generating...')
    embeddings_file_path = '{}.parquet'.format(file_name_prefix)
    if os.path.exists(embeddings_file_path):
        df = pd.read_parquet(embeddings_file_path, engine='pyarrow')
    else:
        filtered_pdf= []
        for row in paper_text:
            if len(row['text']) < 30:
                continue
            if len(row['text']) > 8000:
                row['text'] = row['text'][:8000]
            filtered_pdf.append(row)
        df = pd.DataFrame(filtered_pdf)
        df = df.drop_duplicates(subset=['text', 'page'], keep='first')
        df['length'] = df['text'].apply(lambda x: len(x))

        embedding_model = "text-embedding-ada-002"
        embeddings = []
        for text in tqdm(df.text.values, desc="Generating embeddings"):
                embeddings.append(get_embedding(text, engine=embedding_model))
        df["embeddings"] = embeddings
        # 保存留后续复用embeddings
        df.to_parquet(embeddings_file_path, engine='pyarrow')
    print('embeddings generated DONE...')
    return df

def get_overview(pre_read_content):
    # 输出文章概述
    prompt_messages = []
    prefix = '你是信息分析员'
    i_say = f'对下面的文章片段用中文做概述，文章内容是 ```{pre_read_content}```'

    system_content = {"role": "system", "content": prefix}
    user_content_final = {"role": "user", "content": i_say}
    prompt_messages.append(system_content)
    prompt_messages.append(user_content_final)
    r = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompt_messages)
    res = json.loads(str(r))
    overview = res['choices'][0]['message']['content']
    full_report = "{}{}\n\n".format(full_report, overview)
    print('File Overview: ', overview)
    return overview

def get_questions(prompt_messages):
    # 提出问题
    i_say = f'对这篇文章提出可能的五个问题'

    user_content_final = {"role": "user", "content": i_say}
    prompt_messages.append(user_content_final)
    r = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompt_messages)
    res = json.loads(str(r))
    questions = res['choices'][0]['message']['content']
    full_report = "{}可能的问题：{}\n\n".format(full_report, questions)
    print('5 Qustion Raised: ', questions)
    return questions

def answer_questions(df, qlist, prompt_messages):
    # 对问题逐一回答
    qlist = questions.split('\n')
    qnum = 0
    for question in qlist:
        prompt_messages = []
        prefix = ""
        i_say = prefix + create_prompt(df, question)

        user_content_final = {"role": "user", "content": i_say}
        prompt_messages.append(user_content_final)
        r = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompt_messages)

        answer = r.choices[0]['message']
        res = json.loads(str(r))
        res_status = res['choices'][0]['finish_reason']
        res_content = res['choices'][0]['message']['content']
        answer = res_content
        response = {'answer': answer, 'sources': sources}
        full_report = "{}回答{}：\n{}\n\n".format(full_report, question, response['answer'])
        print("回答{}：\n{}\n\n".format(question, response['answer']))
        
        for source in response['sources']:
            for key, value in source.items():
                full_report = "{}来自原文{}:{}\n\n".format(full_report, key, value)
        qnum = qnum + 1

def ask_question(df, history_filename):
    # custom question answering
    current_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_filename = "{}_chat_{}.md".format(file_name_prefix, current_date_time)

    def ask_question(df, history_filename):
        question = input("Please enter your question: ")
        
        if question.lower() == "exit":
            return None
        
        prompt_messages = []
        history = ""

        prefix = ""
        i_say = prefix + create_prompt(df, question)

        user_content_final = {"role": "user", "content": i_say}
        prompt_messages.append(user_content_final)
        r = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=prompt_messages)

        answer = r.choices[0]['message']
        res = json.loads(str(r))
        res_status = res['choices'][0]['finish_reason']
        res_content = res['choices'][0]['message']['content']
        answer = res_content
        response = {'answer': answer, 'sources': sources}
        print("{}的回答：\n{}\n\n".format(question, response['answer']))
        history = "{}{}".format(history, "{}的回答：\n{}\n\n".format(question, response['answer']))
        for source in response['sources']:
            for key, value in source.items():
                print("来自原文{}:{}\n\n".format(key, value))
                history = "{}{}".format(history, "来自原文{}:{}\n\n".format(key, value))
        # Save conversation history
        with open(history_filename, "a", encoding="utf-8") as file:
            file.write(history)
        return history

def main():
    if len(sys.argv) > 1:
        pdf_file_path = sys.argv[1]
    else:
        print("Please provide a PDF file path as an argument.")
        sys.exit(1)

    pdf_path = pdf_file_path
    file_name_prefix = pdf_path[:-4]

    print('starting...')

    # 读取pdf内容
    paper_text, pre_read_content = extract_pdf_contents(pdf_path)

    # 生成embeddings
    df = generate_embeddings(paper_text, file_name_prefix)
    print('embeddings generated DONE...')

    # 输出文章概述
    overview = get_overview(pre_read_content)
    full_report += f"{overview}\n\n"
    print('File Overview: ', overview)

    # 提出问题
    prompt_messages = create_prompt_messages(overview)
    questions = get_questions(prompt_messages)
    full_report += f"可能的问题：{questions}\n\n"
    print('5 Qustion Raised: ', questions)

    # 对问题逐一回答
    qlist = questions.split('\n')
    full_report += answer_questions(df, qlist, prompt_messages)

    # 保存报告
    current_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "{}_{}.md".format(file_name_prefix, current_date_time)
    with open(filename, "w", encoding="utf-8") as file:
        file.write(full_report)

    # custom question answering
    current_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_filename = "{}_chat_{}.md".format(file_name_prefix, current_date_time)

    while True:
        try:
            ask_question(df, history_filename)
        except KeyboardInterrupt:
            print("\nCtrl+C detected. Exiting the program.")
            break

if __name__ == "__main__":
    main()