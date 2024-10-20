# my-ai-work-graveyard

梳理我的AI work，后续整理到：my-ai-work-graveyard。一方面为记录，另一方面为了看我在这事儿上的做事模式。

**2023-02** 输出文章《闲笔：此刻的期待与担忧》 https://mp.weixin.qq.com/s/Na458CUXjgWAVgeqtqUt0g 后就可以在研究各种玩法。
	    
比如 **2023-04** 乞丐版的RAG实现：《让GPT帮你读文档：一种简单的实现方法》 https://mp.weixin.qq.com/s/7ruOSrscfF6lBIOUQ0kHiw 当时脚本分享了给不少朋友同事，但市场上的产品发展巨快，脚本这类东西会用的人太少了。  
	    
**2023-05** 随即做了微信机器人，当然也是依托开源项目做的，实现了转发公众号文章然后返回总结的功能，只是在开源项目上魔改，这时的代码质量都不算高。  

**2023-05** 还做了件事，将github元数据按一定逻辑扒下来，然后生成报告，并可以将信息推送到企业微信，当然，这些功能的实现都非常简单，现在AI如此先进的情况下，几乎都是一两个小时就能做出来的小玩具。
    
**2023年接下来6、7、8月**时间就没怎么做原创开发，都是在学习和应用各种各样的开源项目，特别是当时能找到的RAG开源项目全部完了一遍，因此也对RAG的各种实现方式有了了解，同步开始使用LangChain，但说实在，变化得实在太快，生产侧应用极其不稳定，所以都依旧是玩具性质。
    
到了 **2023-09**，有朋友在小破站看到火火兔案例之后，问我能不能实在同样的东西。于是上手基于esp-box也做了一个同样的小东西，但当时自己的C语言编程能力不咋滴，终究没法解决中间等待时间过长的问题，再加上硬件部分的朋友总是没时间推进，于是后来项目搁置。  

**2023-12** 之前折腾各种开源项目，包括llama.cpp（本地语音转文字），FastGPT，dify等等项目。
	    
然后参加了一次小范围黑客松活动，因为当时刚在公司推了OpenMetadata（个人认为最好的元数据治理工具，没有之一），本打算在此基础上开发相应的AI模块作为黑客松作品，但被导师批了。  
	    
后来跟另一位同学合作做AI笔记，他负责产品，我负责代码。但因为选了自己完全陌生的iOS开发，最终做出来的东西完成度实在太低。  
    
此时大概已到了2024-02月末，我从2023年底开始焦虑的工作情况已逐步升级。  

**2024-03** 参加第二轮小范围黑客松活动，这次计划了一个基础设施项目，大概可理解为 turn website into xxx (xxx可以是csv、json乃至api)。
	    
**2024-04** 开始学习建站，第一个用了vercel模板twitter-bio上线ship-name-generator.online，但没有去做后续seo优化。  
	    
**2024-06** 响应导航站又用tap4ai的模板做了youraicompanions.com，还是没有持续优化，感觉就是没有感觉（我反思）。  
	    
**2024 07-08月** 又被AI自媒体吸引过去，搞了不少自动化工作流，比如说全自动发头条，全自动分析arXiv论文，全自动分析一个输入主题……期间接触到了斯坦福的storm开源项目，顺带学习dspy，另外通过GNE算法优化了新闻类网站自动化抓取的程序逻辑。这些本都计划在turn-website-into-xxx这个事儿上去集成拓展。  
	    
**2024-09至今**，做了hanyumagicexplainer.net之后，暂无新的产出。受到经济下行冲击，资产受损的中年人还要同时忍受收入下降的煎熬，这是后话了。  

## 清单

- 2023-04 rag-very-basic
- 2023-05 wechat-summary base on chatgpt-on-wechat
- 2023-05 github-crawler
- 2023-09 esp-box-chat base on esp-box
- 2023-12 rainbow-diary
- 2024-09 hanyumagicexplainer

有需要的朋友参考以上清单对应文件夹内容，其他未尽事宜，欢迎小窗交流。