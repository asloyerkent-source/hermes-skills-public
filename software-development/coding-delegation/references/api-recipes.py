# 直连 API 调用配方（绕开 Nous，key 在 Hermes 主目录 .env）
# 读取: load_dotenv(os.path.join(os.environ['HERMES_HOME'],'.env'))
#   GLM_API_KEY  -> api.z.ai  (open.bigmodel.cn)
#   DEEPSEEK_API_KEY -> api.deepseek.com

import os, requests, re
from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ['HERMES_HOME'], '.env'))

GLM_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
DS_URL  = 'https://api.deepseek.com/chat/completions'

# GLM 模型选择经验(2026-08-15 实测):
#   glm-4.7-flash -> 长输出空回(最差)
#   glm-4.6-flash -> 403 限流
#   glm-4-flash   -> 最稳(短输出/写码片段可)
# DS deepseek-chat -> 稳, 但 max_tokens 约1800 会截断长脚本

def call_glm(prompt, model='glm-4-flash', max_tokens=900):
    key = os.environ['GLM_API_KEY']
    body = {'model': model, 'messages': [{'role':'user','content':prompt}],
            'temperature': 0.2, 'max_tokens': max_tokens}
    r = requests.post(GLM_URL, headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},
                     json=body, proxies={'http':None,'https':None}, timeout=90)
    if r.status_code == 200:
        return r.json()['choices'][0]['message']['content']
    return f'ERR {r.status_code}'

def call_ds(prompt, model='deepseek-chat', max_tokens=1500):
    key = os.environ['DEEPSEEK_API_KEY']
    body = {'model': model, 'messages': [{'role':'user','content':prompt}],
            'temperature': 0.1, 'max_tokens': max_tokens}
    r = requests.post(DS_URL, headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},
                     json=body, proxies={'http':None,'https':None}, timeout=150)
    if r.status_code == 200:
        return r.json()['choices'][0]['message']['content']
    return f'ERR {r.status_code}'

# 从模型返回里剥代码块
def extract_code(text):
    m = re.search(r'```python\n(.*?)```', text, re.S) or re.search(r'```\n(.*?)```', text, re.S)
    code = m.group(1) if m else text
    return code.replace('```python','').replace('```','').strip()
