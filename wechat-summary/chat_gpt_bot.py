# encoding:utf-8

import time

import openai
import openai.error
import requests

from bot.bot import Bot
from bot.chatgpt.chat_gpt_session import ChatGPTSession
from bot.openai.open_ai_image import OpenAIImage
from bot.session_manager import SessionManager
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from common.token_bucket import TokenBucket
from config import conf, load_config
from bs4 import BeautifulSoup


# OpenAI对话模型API (可用)
class ChatGPTBot(Bot, OpenAIImage):
    def __init__(self):
        super().__init__()
        # set the default api_key
        openai.api_key = conf().get("open_ai_api_key")
        if conf().get("open_ai_api_base"):
            openai.api_base = conf().get("open_ai_api_base")
        proxy = conf().get("proxy")
        if proxy:
            openai.proxy = proxy
        if conf().get("rate_limit_chatgpt"):
            self.tb4chatgpt = TokenBucket(conf().get("rate_limit_chatgpt", 20))

        self.sessions = SessionManager(ChatGPTSession, model=conf().get("model") or "gpt-3.5-turbo")
        self.args = {
            "model": conf().get("model") or "gpt-3.5-turbo",  # 对话模型的名称
            "temperature": conf().get("temperature", 0.9),  # 值在[0,1]之间，越大表示回复越具有不确定性
            # "max_tokens":4096,  # 回复最大的字符数
            "top_p": 1,
            "frequency_penalty": conf().get("frequency_penalty", 0.0),  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            "presence_penalty": conf().get("presence_penalty", 0.0),  # [-2,2]之间，该值越大则更倾向于产生不同的内容
            "request_timeout": conf().get("request_timeout", None),  # 请求超时时间，openai接口默认设置为600，对于难问题一般需要较长时间
            "timeout": conf().get("request_timeout", None),  # 重试超时时间，在这个时间内，将会自动重试
        }

    def get_wechat_url(self, url):
        text = ""
        try:
            # Fetch the page content
            response = requests.get(url)
            content = response.content
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            # Extract and append text from all paragraph tags to the text string
            for paragraph in soup.select('div[id="page-content"]'):
                text += paragraph.get_text(strip=True) + "\n"
            return True, text
        except Exception as e:
            logger.error("[CHATGPT] get_wechat_url error: {}".format(e))
            return False, "获取微信文章失败"

    def reply(self, query, context=None):
        # acquire reply content
        if context.type == ContextType.TEXT:
            logger.info("[CHATGPT] query={}".format(query))

            session_id = context["session_id"]
            reply = None
            clear_memory_commands = conf().get("clear_memory_commands", ["#清除记忆"])
            if query in clear_memory_commands:
                self.sessions.clear_session(session_id)
                reply = Reply(ReplyType.INFO, "记忆已清除")
            elif query == "#清除所有":
                self.sessions.clear_all_session()
                reply = Reply(ReplyType.INFO, "所有人记忆已清除")
            elif query == "#更新配置":
                load_config()
                reply = Reply(ReplyType.INFO, "配置已更新")
            if reply:
                return reply
            session = self.sessions.session_query(query, session_id)
            logger.debug("[CHATGPT] session query={}".format(session.messages))

            api_key = context.get("openai_api_key")

            # if context.get('stream'):
            #     # reply in stream
            #     return self.reply_text_stream(query, new_query, session_id)

            reply_content = self.reply_text(session, api_key)
            logger.debug(
                "[CHATGPT] new_query={}, session_id={}, reply_cont={}, completion_tokens={}".format(
                    session.messages,
                    session_id,
                    reply_content["content"],
                    reply_content["completion_tokens"],
                )
            )
            if reply_content["completion_tokens"] == 0 and len(reply_content["content"]) > 0:
                reply = Reply(ReplyType.ERROR, reply_content["content"])
            elif reply_content["completion_tokens"] > 0:
                self.sessions.session_reply(reply_content["content"], session_id, reply_content["total_tokens"])
                reply = Reply(ReplyType.TEXT, reply_content["content"])
            else:
                reply = Reply(ReplyType.ERROR, reply_content["content"])
                logger.debug("[CHATGPT] reply {} used 0 tokens.".format(reply_content))
            return reply

        elif context.type == ContextType.IMAGE_CREATE:
            ok, retstring = self.create_img(query, 0)
            reply = None
            if ok:
                reply = Reply(ReplyType.IMAGE_URL, retstring)
            else:
                reply = Reply(ReplyType.ERROR, retstring)
            return reply
        elif context.type == ContextType.WECHAT_URL:
            ok, urlcontent = self.get_wechat_url(query)
            reply = None
            if ok:
                logger.info("[CHATGPT] query={}".format(urlcontent))

                session_id = context["session_id"]
                session = self.sessions.session_query(urlcontent, session_id)
                api_key = context.get("openai_api_key")
                cur_tokens = session.calc_tokens() # 计算当前session已用的token数
                logger.info("[魔改part] cur_tokens={}".format(cur_tokens))
                max_tokens = 3096 # 获取当前session的最大token数
                if cur_tokens > max_tokens:
                    separate_part_num = 1
                    while cur_tokens / separate_part_num > max_tokens: # 如果当前session已用的token数大于最大token数，计算切分段落数
                        separate_part_num += 1
                    # 将urlcontent切分为n段，每段最多max_tokens个token
                    urlcontent_list = [urlcontent[i:i + max_tokens] for i in range(0, len(urlcontent), max_tokens)]
                    midd_content = ""
                    for i in range(len(urlcontent_list)):
                        logger.info("[魔改part] 分段{}搞紧".format(i))
                        # 遍历每段，分别调用reply_text，将返回的content组合成新的prompt
                        msg_temp = [{"role": "system", "content": "你是读书笔记高手,请总结以下文本要点,风格严谨有逻辑,语言平实易理解,以有序列表形式输出:"}, {"role": "user", "content": urlcontent_list[i]}]
                        # res_tmp = openai.ChatCompletion.create(api_key=api_key, messages="你是信息分析专家,请总结以下文本要点,以有序列表形式输出:"+urlcontent_list[i], **self.args)
                        res_tmp = openai.ChatCompletion.create(api_key=api_key, messages=msg_temp, **self.args)
                        logger.info("[魔改part] 分段{}结果".format(res_tmp.choices[0]["message"]['content']))
                        midd_content = midd_content + res_tmp.choices[0]["message"]['content']
                        logger.info("[魔改part] 分段{}搞完".format(i))
                    urlcontent = "你是读书笔记高手,风格严谨有逻辑,语言平实易理解,请汇总以下文本为4到8个要点,以有序列表形式输出:" + midd_content
                else:
                    urlcontent = "你是读书笔记高手,风格严谨有逻辑,语言平实易理解,请汇总以下文本为4到8个要点,以有序列表形式输出:" + urlcontent
                # 调用reply_text，返回reply_content
                logger.info("[魔改part] 重建session")
                logger.info("[魔改part] 最后汇总prompt={}".format(urlcontent))
                session = self.sessions.session_query(urlcontent, session_id)
                logger.debug("[CHATGPT] session query={}".format(session.messages))
                reply_content = self.reply_text(session, api_key)
                logger.debug(
                    "[CHATGPT] new_query={}, session_id={}, reply_cont={}, completion_tokens={}".format(
                        session.messages,
                        session_id,
                        reply_content["content"],
                        reply_content["completion_tokens"],
                    )
                )
                if reply_content["completion_tokens"] == 0 and len(reply_content["content"]) > 0: # 有回复但是用完了
                    reply = Reply(ReplyType.ERROR, reply_content["content"])
                elif reply_content["completion_tokens"] > 0: # 有回复且没用完
                    self.sessions.session_reply(reply_content["content"], session_id, reply_content["total_tokens"])
                    reply = Reply(ReplyType.TEXT, reply_content["content"])
                else: # 没有回复
                    reply = Reply(ReplyType.ERROR, reply_content["content"])
                    logger.debug("[CHATGPT] reply {} used 0 tokens.".format(reply_content))
            else:
                reply = Reply(ReplyType.ERROR, urlcontent)
            return reply
        else:
            reply = Reply(ReplyType.ERROR, "Bot不支持处理{}类型的消息".format(context.type))
            return reply

    def reply_text(self, session: ChatGPTSession, api_key=None, retry_count=0) -> dict:
        """
        call openai's ChatCompletion to get the answer
        :param session: a conversation session
        :param session_id: session id
        :param retry_count: retry count
        :return: {}
        """
        try:
            if conf().get("rate_limit_chatgpt") and not self.tb4chatgpt.get_token():
                raise openai.error.RateLimitError("RateLimitError: rate limit exceeded")
            # if api_key == None, the default openai.api_key will be used
            response = openai.ChatCompletion.create(api_key=api_key, messages=session.messages, **self.args)
            # logger.info("[ChatGPT] reply={}, total_tokens={}".format(response.choices[0]['message']['content'], response["usage"]["total_tokens"]))
            return {
                "total_tokens": response["usage"]["total_tokens"],
                "completion_tokens": response["usage"]["completion_tokens"],
                "content": response.choices[0]["message"]["content"],
            }
        except Exception as e:
            need_retry = retry_count < 2
            result = {"completion_tokens": 0, "content": "我现在有点累了，等会再来吧"}
            if isinstance(e, openai.error.RateLimitError):
                logger.warn("[CHATGPT] RateLimitError: {}".format(e))
                result["content"] = "提问太快啦，请休息一下再问我吧"
                if need_retry:
                    time.sleep(20)
            elif isinstance(e, openai.error.Timeout):
                logger.warn("[CHATGPT] Timeout: {}".format(e))
                result["content"] = "我没有收到你的消息"
                if need_retry:
                    time.sleep(5)
            elif isinstance(e, openai.error.APIConnectionError):
                logger.warn("[CHATGPT] APIConnectionError: {}".format(e))
                need_retry = False
                result["content"] = "我连接不到你的网络"
            else:
                logger.warn("[CHATGPT] Exception: {}".format(e))
                need_retry = False
                self.sessions.clear_session(session.session_id)

            if need_retry:
                logger.warn("[CHATGPT] 第{}次重试".format(retry_count + 1))
                return self.reply_text(session, api_key, retry_count + 1)
            else:
                return result


class AzureChatGPTBot(ChatGPTBot):
    def __init__(self):
        super().__init__()
        openai.api_type = "azure"
        openai.api_version = "2023-03-15-preview"
        self.args["deployment_id"] = conf().get("azure_deployment_id")

    def create_img(self, query, retry_count=0, api_key=None):
        api_version = "2022-08-03-preview"
        url = "{}dalle/text-to-image?api-version={}".format(openai.api_base, api_version)
        api_key = api_key or openai.api_key
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        try:
            body = {"caption": query, "resolution": conf().get("image_create_size", "256x256")}
            submission = requests.post(url, headers=headers, json=body)
            operation_location = submission.headers["Operation-Location"]
            retry_after = submission.headers["Retry-after"]
            status = ""
            image_url = ""
            while status != "Succeeded":
                logger.info("waiting for image create..., " + status + ",retry after " + retry_after + " seconds")
                time.sleep(int(retry_after))
                response = requests.get(operation_location, headers=headers)
                status = response.json()["status"]
            image_url = response.json()["result"]["contentUrl"]
            return True, image_url
        except Exception as e:
            logger.error("create image error: {}".format(e))
            return False, "图片生成失败"
