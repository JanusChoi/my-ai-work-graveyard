import requests
import os,sys,time
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
import datetime
from collections import defaultdict
import configparser
import pymongo
from tqdm import tqdm
import matplotlib.pyplot as plt
import logging

import openai
from langchain.document_loaders import UnstructuredFileLoader
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain import OpenAI
from langchain.chat_models import AzureChatOpenAI
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)

logging.basicConfig(filename='./_data_workflow/basic_data_staging.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 运行环境初始化
os.environ["http_proxy"] = "http://127.0.0.1:1088"
os.environ["https_proxy"] = "http://127.0.0.1:1088"
os.environ["OPENAI_API_KEY"] = "your_key"

BASE_URL = "https://myapp.openai.azure.com/"
API_KEY = "your_key"
DEPLOYMENT_NAME = "gpt-35-turbo"

#################### 通知模块
def push_wecom(content):
    msg = '{""msgtype"":""markdown"",""markdown"":{""content"":' + content + '}}'
    msg = '{"msgtype":"markdown","markdown":{"content":"' + content + '"}}'
    os_command = 'curl \'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key\' \
    -H \'Content-Type: application/json\' \
    -d \'' + msg + '\''
    os.system(os_command)
    time.sleep(0.2)

# 接口数据mapping
def extract_info(item):
    owner, repo = item['hl_name'].replace('</em>','').replace('<em>','').split('/')
    access_url = f"https://github.com/{owner}/{repo}"
    description = item['hl_trunc_description']
    is_organization = item['owned_by_organization']
    language = item['language']
    stars = item['followers']
    topics = item['topics']
    
    return {
        'owner': owner,
        'repo':repo,
        'access_url':access_url,
        'description': description,
        'is_organization': is_organization,
        'language': language,
        'stars': stars,
        'topics': topics
    }

# 接口数据mapping
def extract_info_api(item):
    try:
        owner = item['owner']['login']
        repo = item['name']
        access_url = item['html_url']
        description = item['description']
        is_organization = item.get('organization', {}).get('type', '') == 'Organization'
        language = item['language']
        stars = item['stargazers_count']
        topics = item['topics']
        created_at = item['created_at']
        updated_at = item['updated_at']
        size = item['size']
        has_wiki = item['has_wiki']
        forks_count = item['forks_count']
        open_issues_count = item['open_issues_count']
        if item.get('license', {}) is not None:
            license_name = item.get('license', {}).get('name', {})
        else:
            license_name = "no license"

        return {
            'owner': owner,
            'repo':repo,
            'access_url':access_url,
            'description': description,
            'is_organization': is_organization,
            'language': language,
            'stars': stars,
            'topics': topics,
            'created_at': created_at,
            'updated_at': updated_at,
            'size': size,
            'has_wiki': has_wiki,
            'forks_count': forks_count,
            'open_issues_count': open_issues_count,
            'license_name': license_name
        }
    except Exception as e:
        print(f"Error occurred while extracting info from item: {item}")
        raise e

# 处理 mongo 连接
class mongo_connector:
    def __init__(self, server_profiles):
        self.mongo_host = ''
        self.mongo_database = ''
        self.mongo_client = ''
        self.start_time = datetime.datetime.now()
        self.end_time = datetime.datetime.now() + datetime.timedelta(minutes=40)
        
        self.server_profiles = server_profiles
    
    def get_config(self):
        """读取配置文件获取相关信息"""
        print("连接环境：{}".format(self.server_profiles))
        cf = configparser.ConfigParser()
        cf.read("/Users/januswing/code/awesome-gpt-dev/_data_workflow/config.ini")
        
        self.mongo_host = 'mongodb://{}:{}/'.format(cf.get(self.server_profiles, 'mongo_host'), cf.get(self.server_profiles, 'mongo_port'))
        self.mongo_database = cf.get(self.server_profiles, 'mongo_database')
        self.mongo_client = pymongo.MongoClient(self.mongo_host)[self.mongo_database]

def web_advsearch(base_url):
    project_data = []
    page = 1
    while True:
        print(f"正在爬取第{page}页")
        url = base_url + str(page)

        headers = {
        'authority': 'github.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'max-age=0',
        'cookie': 'your_cookies',
        'if-none-match': 'W/"866a4073e03db5ba881df79c53a090be"',
        'referer': 'https://github.com/search/advanced',
        'sec-ch-ua': '"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.68'
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            embedded_data = soup.find('script', {'type': 'application/json', 'data-target': 'react-app.embeddedData'})
            data = json.loads(embedded_data.string)
            search_results = data['payload']['results']
            items = search_results
            if items == []:
                break
            for item in items:
                project_info = extract_info(item)
                project_data.append(project_info)
        else:
            print(f"Failed to fetch data: {response.status_code}, {response.reason}, {response.url}")
        time.sleep(1)
        page += 1
    return project_data

# 构造查询url
def construct_url(created, stars, label):
    return "https://github.com/search?q=GPT+OR+LLM+OR+Transformer+OR+\"large+language+model\"+stars%3A>1000&type=repositories&ref=advsearch&s=stars&o=desc&p="

# 提取项目所有commits数据，按天汇总
def get_repo_commits(owner, repo):
    commits_by_date = defaultdict(int)
    base_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "token your_github_token"
    }
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}, {response.reason}, {response.url}")
            break

        data = json.loads(response.text)
        if not data:  # If the response data is empty, we've reached the end of the commits list
            break

        for commit in data:
            date_str = commit['commit']['author']['date']
            date = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ').date()
            commits_by_date[date] += 1

        page += 1
    print(f"Found {len(commits_by_date)} commit dates for {owner}/{repo}.")

    return dict(commits_by_date)

# 输出项目url，返回ReadMe总结及三个限定范围内的标签
"""
{
    "repo_summary": "{summary_text}",
    "repo_tag1": "",
    "repo_tag2": "",
    "repo_tag3": ""
}
"""
def get_repo_summary(access_url):
    print(f"getting summary from repo:{access_url}")
    url = access_url.replace("github.com", "raw.githubusercontent.com").replace("/tree/", "/") + "/master/README.md"
    try:
        readme_txt = requests.get(url).text
    except:
        logging.ERROR(f"Error fetching or processing {url}, exeption: {sys.exc_info()[0]}")

    with open("/Users/januswing/data/tmp_readme.txt", "w") as f:
        f.write(readme_txt)
    f.close()
    # 初始化文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 2000,  # 一个chunk的大小
        chunk_overlap = 200 # 包含多少上一个chunk结尾的内容
    )

    # 切分文本
    with open("/Users/januswing/data/tmp_readme.txt") as f:
        readme_file = f.read()
    readme_texts = text_splitter.split_text(readme_file)

    readme_docs = [Document(page_content=t) for t in readme_texts]

    chat = ChatOpenAI(model_name="gpt-3.5-turbo", max_tokens=2048)

    # 创建总结链
    chain = load_summarize_chain(chat, chain_type="map_reduce", verbose=False)

    # 执行总结链
    print(f"starting chain with readme_docs total size={len(readme_docs)}")
    if len(readme_docs) > 8:
        readme_docs = readme_docs[:8]
    summarization_eng = chain.run(readme_docs)

    chat_template="""
    You are a helpful assistant.
    """
    chat_prompt="请将以下文本翻译为中文{}".format(summarization_eng)

    # chat = ChatOpenAI(model_name="gpt-3.5-turbo", max_tokens=2048)

    messages = [
        SystemMessage(content=chat_template),
        HumanMessage(content=chat_prompt)
    ]
    print("summary done")
    summarization_chn = chat(messages).content
    
    project_tags = """
    autonomous	GPT自动化
    algorithm	算法实现
    selfhostLLM	低成本自托管LLM
    academic	学术工作辅助
    Image recognition	图像识别相关
    mirror	镜像或备份站
    text-to-speech	语音识别相关
    plugin	插件
    code	代码工具
    awesome-list	清单，学习资料
    fine-tune	模型微调
    game	游戏相关
    prompt	提示词工程
    data	数据处理
    industry	行业特定应用
    IMbot	嵌入工具中的机器人
    Education	教育相关应用
    NA	不相关
    """

    chat_prompt="""你是一个资深github玩家，同时也是一位全栈工程师。请根据这一套开源项目分类{}，判断以下项目ReadMe内容，给出5个合理的标签，并标记标签可能性的概率(两位小数)，请用json格式输出你的结果，只输出json数据结果即可：{}""".format(project_tags, summarization_chn)
    # chat = ChatOpenAI(model_name="gpt-3.5-turbo", max_tokens=2048)
    messages = [
        SystemMessage(content=chat_template),
        HumanMessage(content=chat_prompt)
    ]
    tags_json = chat(messages)
    # 获取分值最高的三个tag
    try:
        tags_json = json.loads(tags_json.content)
        top_tags = sorted(tags_json, key=tags_json.get, reverse=True)[:3]
        repo_summary = {
            "repo_summary": summarization_chn,
            "repo_tag1": top_tags[0],
            "repo_tag2": top_tags[1],
            "repo_tag3": top_tags[2]
        }
        print("repo tagged")
    except Exception as e:
        print(f"getting top_tags failed, json format may be invalid:{e}")
        repo_summary = {
            "repo_summary": summarization_chn,
            "repo_tag1": "json invalid",
            "repo_tag2": "json invalid",
            "repo_tag3": "json invalid"
        }
    return repo_summary

# 统一通过GitHub API获取项目信息
def get_repo_info(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {'Authorization': 'Bearer your_token'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        p = json.loads(response.text)
        p = extract_info_api(p)
        p['sync_time'] = datetime.datetime.now().strftime("%Y-%m-%d")
        return p
    else:
        # 如果找不到对应的项目，则报错，说明该项目的注册信息在GitHub上已被更改
        return 999

if __name__ == '__main__':
    logging.info("start to sync github project data...")

    # get input parameters
    env = sys.argv[1] # 环境 dev/uat/prd
    # 获取输入的github url
    if len(sys.argv) > 2:
        new_url = sys.argv[2]
        logging.info('adding repo manually: new_url: %s', new_url)
    else:
        new_url = None

    sync_time = datetime.datetime.now().strftime("%Y-%m-%d_%H|%M|%S")
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mongo_conn = mongo_connector(env)
    mongo_conn.get_config()
    mg_stage = mongo_conn.mongo_client
    tb_dim_github_project = mg_stage['dim_github_project']
    tb_his_github_project = mg_stage['his_github_project']
    tb_fact_github_project = mg_stage['fact_github_project']

    if new_url == None:
        logging.info("getting all related project data and update existing")
        # 获取项目信息
        created = '2023-03-01'
        stars = '%3A%3E1000'
        label = 'GPT'
        url = construct_url(created, stars, label)
        all_related_projects = web_advsearch(url)
        push_content = []
        # 将 all_related_projects 转换为字典
        related_projects_dict = {(p['owner'], p['repo']): p for p in all_related_projects}
        # 更新所有现存项目信息
        count = 0
        for project in tqdm(tb_dim_github_project.find()):
        # for project in tqdm(tb_dim_github_project.find({"summary": {"$exists": False}})):
            # if count < 580:
            #     count += 1
            #     continue
            owner = project['owner']
            repo = project['repo']
            current_stars = project['stars']
            p = get_repo_info(owner, repo)
            if p != 999:
                latest_stars = p['stars']
                if 'summary' not in project:
                    tmp_data = get_repo_summary(f"https://github.com/{owner}/{repo}")
                    p['summary'] = tmp_data['repo_summary']
                    p['tag1'] = tmp_data['repo_tag1']
                    p['tag2'] = tmp_data['repo_tag2']
                    p['tag3'] = tmp_data['repo_tag3']
                else:
                    # print(f"skipping project with column summary:{owner}/{repo}")
                    pass
                if latest_stars - current_stars > 200:
                    logging.info(f"Growing Project over 200 stars today: https://github.com/{owner}/{repo}")
                    description = p['description']
                    push_content.append(f"✅Growing Project over 200 stars today: [{repo}](https://github.com/{owner}/{repo})\n🌟{latest_stars}\nhttps://github.com/{owner}/{repo}\n{description}")
                p['sync_time'] = datetime.datetime.now().strftime("%Y-%m-%d")
                tb_dim_github_project.update_one({'owner':owner, 'repo':repo}, {'$set':p})
                tb_his_github_project.insert_one(p)
            else:
                # 如果找不到对应的项目，则报错，说明该项目的注册信息在GitHub上已被更改
                logging.error("Project Not exist on github anymore Owner=%s, Repo=%s", owner, repo)
                continue
            
        # 每五条信息整合推送，不满五条则直接推送
        for i, push in enumerate(push_content):
            if i % 5 == 0:
                ready_to_push = ""
            ready_to_push += ''.join(push) + '\n'
            if (i + 1) % 5 == 0 or i == len(push_content) - 1:
                push_wecom(ready_to_push)
        
        # 将新数据插入到dim_github_project表中
        for project in all_related_projects:
            owner = project['owner']
            repo = project['repo']
            stars = project['stars']
            description = project['description']
            # 判断是否已经存在于dim_github_project表中
            if tb_dim_github_project.find_one({'owner': owner, 'repo': repo}):
                continue
            else:
                # 统一通过GitHub API获取项目信息
                url = f"https://api.github.com/repos/{owner}/{repo}"
                headers = {'Authorization': 'Bearer your_token'}
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    p = json.loads(response.text)
                    p = extract_info_api(p)
                    latest_stars = p['stars']
                    if 'summary' not in project:
                        tmp_data = get_repo_summary(f"https://github.com/{owner}/{repo}")
                        p['summary'] = tmp_data['repo_summary']
                        p['tag1'] = tmp_data['repo_tag1']
                        p['tag2'] = tmp_data['repo_tag2']
                        p['tag3'] = tmp_data['repo_tag3']
                    p['sync_time'] = datetime.datetime.now().strftime("%Y-%m-%d")
                    # 插入dim_github_project表
                    tb_dim_github_project.insert_one(p)
                    # 插入his_github_project表
                    tb_his_github_project.insert_one(p)
                logging.info(f"New Project inserted: https://github.com/{owner}/{repo}")
                push_wecom(f"New Project inserted: [{repo}](https://github.com/{owner}/{repo})\n🌟{stars}\nhttps://github.com/{owner}/{repo}\n{description}")

        # 获取前50个星级项目
        top_projects = list(tb_dim_github_project.find().sort([('stars', pymongo.DESCENDING)]).limit(50))

        # 生成图表
        x = [project['repo'] for project in top_projects]
        y = [project['stars'] for project in top_projects]
        plt.figure(figsize=(24, 12))
        plt.bar(x, y)
        plt.xticks(rotation=45, ha='right') # 将横轴文字倾斜并竖向排列
        # 调整横轴文字的颜色
        for i, tick in enumerate(plt.gca().get_xticklabels()):
            if i % 2 == 0:
                tick.set_color('blue')
            else:
                tick.set_color('red')
        plt.xlabel('Project')
        plt.ylabel('Stars')
        plt.title('Top 50 Stars Projects')
        plt.tight_layout()

        # 保存图表为PNG格式，并在文件名中添加时间戳
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f'top_stars_projects_{timestamp}.png'

        # 在图片的右上角添加时间戳
        plt.text(0.95, 0.95, timestamp, transform=plt.gca().transAxes, ha='right', va='top')

        plt.savefig(filename)
    else:
        # 解析github url，获取owner和repo
        owner, repo = new_url.split('/')[-2:]

        # 判断该项目是否已经存在于表中
        if tb_dim_github_project.find_one({'owner': owner, 'repo': repo}):
            print("Project already exists in the table.")
        else:
            # 如果不存在，则通过GitHub API获取项目信息
            # 统一通过GitHub API获取项目信息
            url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {'Authorization': 'Bearer your_token'}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                p = json.loads(response.text)
                p = extract_info_api(p)
                latest_stars = p['stars']
                tmp_data = get_repo_summary(f"https://github.com/{owner}/{repo}")
                p['summary'] = tmp_data['repo_summary']
                p['tag1'] = tmp_data['repo_tag1']
                p['tag2'] = tmp_data['repo_tag2']
                p['tag3'] = tmp_data['repo_tag3']
                p['sync_time'] = datetime.datetime.now().strftime("%Y-%m-%d")
                # 插入dim_github_project表
                tb_dim_github_project.insert_one(p)
                # 插入his_github_project表
                tb_his_github_project.insert_one(p)
                logging.info(f"New Project inserted: https://github.com/{owner}/{repo}")
            else:
                # 如果找不到对应的项目，则报错，说明该项目的注册信息在GitHub上已被更改
                logging.error(f"Project does not exist on GitHub anymore: Owner={owner}, Repo={repo}")
    logging.info("Task finished")
    