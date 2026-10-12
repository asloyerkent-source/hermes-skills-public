# Holographic 事实去重/整理（安全做法）

## 背景
VAULT 6996文件经 LongCat 提炼写入 Holographic，得 3.6万+ 事实。用户感觉"很多重复/无意义"，尝试整理。

## 实测结论

### 1. 逐字重复 = 0
喂养脚本写前搜相似去重已生效，无逐字重复。

### 2. 噪声碎片 = 112条（安全删）
极短(<8字)里约112条是纯统计碎片："X月共N条消息"/"共发送N条消息"。
正则识别 `^\d+月(有|消息共)` / `消息共\d+条` / `条消息$` → 全删，零损失。
保留的短事实（"大货交期35天""校验通过"）有信息量，不动。

### 3. 近似重复 = 不能盲目合并（关键坑）
- **朴素聚类（前N字相同）**：估4047条/占12.8%，但**误删真实事件**。
  反例："合同号AA15024002"vs"AA09624065"（不同合同）、"总金额177010"vs"278070"（不同订单）、"5月20日发图"vs"11月20日发图"（不同日期）——全被当重复删。
- **Jaccard+实体保护**：去掉长数字串后算相似，仍把"X月X日发送了一张图片"各日期合并（日期不同=不同事件）。
- **结论**：聊天流水事实"结构相似但实体不同"不是重复，是不同事件。全自动语义合并在聊天数据上**不可靠，会毁数据**。

### 4. 安全合并 = 去标点完全等价（唯一可信任的）
```
norm(c) = re.sub(r'[\s，。、！？：:；;]','',c).lower()
按 norm(c) 分组，组>1 则除首条外全删
```
实测 59 组真重复，全是"仅差标点/大小写"：
- "3月30日发送了AF_LOGO的AI文件" vs "...ai文件"
- "7月17日发货预计7月19日到达" vs "7月17日发货，预计7月19日到达"
- "BIC 4.6万个箱唛资料已发送" vs "BIC4.6万个箱唛资料已发送"
实体100%一致，删零损失。约几十~几百条量级。

## 操作脚本（dry-run 先确认再执行）
```python
import sqlite3, re
from collections import defaultdict
conn = sqlite3.connect(db_path)
rows = conn.execute('select fact_id, content, category from facts').fetchall()
def norm(c): return re.sub(r'[\s，。、！？：:；;]','',c).lower()
g = defaultdict(list)
for fid,c,cat in rows: g[norm(c)].append((fid,c,cat))
del_ids=[]; bk=[]
for k,v in g.items():
    if len(v)>1:
        for fid,c,cat in v[1:]:
            del_ids.append(fid); bk.append({'fact_id':fid,'content':c,'category':cat})
# 先 dump bk 给用户看，确认无误再:
# for fid in del_ids: conn.execute('delete from facts where fact_id=?',(fid,)); conn.commit()
```

## 王浩事实清理判定逻辑（用户逐类指令）
- 身份证/支付宝/手机/地址：每类**留1条**，其余删
- 家人（老婆相关）：**全删**
- 公司/职务：合并去重（保留涨薪/下属/公司名代表）
- 样品收发：配到对方地址/电话/公司抬头的**留**，配不到的**删**
- 行踪：只留香港相关，其余删
- 健康：LongCat 误归因"王浩新冠"的**删**，正确记录（用户本人新冠）存 `~/.hermes/health_archive.md`（本地红线隔离，不进 holographic）

## 备份约定
每次删除先 dump 到 `~/HermesShare/王浩已删_批次N_*.json` 或 `全库*_批次*.json`。
⚠ 备份文件含敏感信息，本身是敏感文件，别同步到云。
