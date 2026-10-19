"""Original vector diagrams; all numerical scales are teaching assumptions."""
import html,textwrap
def esc(s):return html.escape(str(s))
FIGS={
'architecture':('全局架构：控制流、计算流与内存归属',[
('HTTP 前端 / Tokenizer（CPU）','messages → 模板 → token ids','uid、采样参数、回复通道'),
('Scheduler（CPU 控制，含 GPU 表）','等待队列 → 选 batch → 分配缓存','Req / Batch / 页表 / 状态槽'),
('Engine / 模型层（GPU 主干）','Embedding → Attention → MoE → LM head','KV 或递归状态按请求保存'),
('MoE 专家层（跨 CPU / GPU）','router → cache → fill 或 CPU compute','host banks 为权重源；GPU slots 为副本'),
('Sampler → 结果提交 → Detokenizer','next id → stop 判断 → 增量文本','释放活动引用；可保留可复用前缀')]),
'math':('MoE 的张量链：路由决定专家，专家结果加权合并',[
('输入 H：N×D；本例 1×4','router W：4×8；H @ W → logits','softmax → 选 top-2，得到 ids 与权重'),
('专家 e 的门控前馈','gate / up：4×6；两路输出 1×6','SiLU(gate) ⊙ up → 中间表示 1×6'),
('down：6×4 → 专家输出 1×4','每个被选择专家分别计算','路由权重相乘、求和 → 1×4'),
('放置策略只改变谁来算','GPU 计算 H∪F；CPU 计算 C','保持同一组专家和权重；允许舍入误差')]),
'request':('统一请求：生成 id 与算出该位置的 KV 是两件事',[
('教学 prompt：小猫 / 喜欢 / 吃','自定义 ids=[11,10,7]；位置 0,1,2','已知 3；已计算 0'),
('Prefill 计算位置 0..2','最后一个 hidden → logits → 选择 8 鱼','已知 4；已计算 3；8 尚未有 KV'),
('Decode 只输入 id 8，位置 3','Q 查历史 KV；写新 KV；选择 1 EOS','已知 5；已计算 4；EOS 无需再前向'),
('提交终止结果，回收活动资源','不把停止 token 当作下一轮输入','文本输出与缓存生命周期分开管理')]),
'loading':('启动数据流：磁盘权重到运行时可读的专家 banks',[
('配置与架构识别','checkpoint config → 模型注册 / 量化方案','明确 dtype、attention 类型、expert layout'),
('磁盘 → 最终 host banks','专家权重按 kernel 所需布局装载','数据到位后 pin / lock；关注系统内存'),
('GPU 常驻主干与专家 slots','non-expert weights + KV / 状态池','slot 是 bank 中同一专家各张量的行集合'),
('预热、捕获、复位、开始服务','构建 CPU executor 与稳定 I/O 地址','内核预热不等于所有专家长期留在显存')]),
'cache':('专家缓存：逻辑身份与物理位置必须分开',[
('router ids：本层 [1,3]','完整身份：(layer,e)，例如 (2,3)','扁平 key = layer×E+expert'),
('查 slot_for_id / id_of_slot','命中保留；缺失去重；选择可替换槽','不能驱逐本步仍要使用的命中专家'),
('准备 src_indices / evict_slots','源是 host 当前层 expert 行','目标是对应 pool 的 GPU slot 行'),
('copy_missing 后再 GEMM','bank 列表共用同一组 src/dst 索引','topk_ids 原地改写：expert id → slot id'),
('当前版本支持多个 pool','unified 按兼容 layout 分组','per-layer 则逐层分组；不是任意布局互换')]),
'hybrid':('混合执行：每条 route 恰好被一个分支计算',[
('一次路由先分 H / M','H：命中；M：唯一缺失专家集合','同一专家被多个 token 选中只计一次 miss'),
('从 M 选择 F，剩余交给 C','F：搬到 GPU；C=M−F：CPU 计算','GPU 集合 H∪F；CPU 集合 C；两者不重叠'),
('先提交 CPU，再发起 GPU 工作','CPU：D2H 小输入 → host bank GEMV','GPU：copy_missing → expert GEMM'),
('同步并合并部分和','gpu_w 对 CPU route 为 0','cpu_ids 对 GPU route 为 −1；Y=Ygpu+Ycpu'),
('q 的选择由有效带宽决定','先平衡时间，再取整数与容量上限','当前源码可从并发 profile 得到 fetch fraction')]),
'graph':('动态路由如何进入固定地址的 CUDA Graph',[
('捕获：按支持 batch size 建图','稳定 input / position / metadata buffers','动态的内容存入同一块地址'),
('回放前：复制本步输入','新的 ids / positions / page table 元数据','padding 是图形状选择，不是新用户请求'),
('回放中：GPU 判断命中与搬运量','固定形状索引缓冲 + 设备端 count','不是把上一轮的路由结果写死在图中'),
('CPU 分支也需要顺序协议','固定 pinned I/O；发布 / 等待 / 合并','按能力探测选择 memop / kernel / host node'),
('容量重建会使旧图失效','先排空在途 batch → 重新分配 → 重捕获','图捕获安全性取决于地址与同步协议')]),
'kv':('两种缓存：权重缓存与请求状态缓存互不替代',[
('专家权重缓存','key=(layer,expert)；内容是参数','跨请求复用；host bank 为来源'),
('分页 KV 缓存（普通全注意力）','key 含 token 前缀；内容是过去的 K/V','位置 p → page floor(p/P) + offset'),
('线性注意力 / 递归状态','s_t = f(s_(t−1),x_t)','需要某个前缀末尾的快照；不是 K/V 列表'),
('请求结束后的两层释放','撤销活动引用不一定立即抹去所有缓存','可复用前缀由 prefix cache 生命周期管理')]),
'anchor':('边界状态复用：精确前缀匹配，而非语义相似度检索',[
('旧请求 tokens 长度 10','已有 checkpoint 位于长度 4、6、10','每个快照只对对应的精确前缀成立'),
('新请求前 7 个 token 相同','位置 7 之后被工具结果改写','长为 10 的旧快照已不可用'),
('选可恢复的最近边界：长度 6','把快照复制到活跃请求状态槽','树节点快照不允许被新请求原地污染'),
('从位置 6 重算新后缀','新请求长度 9 → 需处理 3 个 token','KV 可匹配长度与递归状态可恢复长度不同')]),
'memory':('显存预算：同一张卡上的多个池要共同结账',[
('总显存 / 空闲显存不是同一量','启动时空闲量 + memory ratio + 已分配量','同时观察其他进程与运行时分配'),
('预留：主干、工作区、图、余量','非专家权重与中间张量也要占空间','专家量化小不代表整模型按同一比例缩小'),
('为 KV / 状态池和专家池分配','长度 / batch 改变所需缓存资源','专家池更大可能挤压请求状态容量'),
('运行时修改只能在安全点','Scheduler 等无在途 batch、无待执行请求','校验 → 重建池与图 → 恢复接收')]),
'serving':('结束不是丢一个 id：提交与取消都有资源顺序',[
('Engine 输出 next id + copy_done','GPU 写 token_pool；异步复制到 CPU','调度计数可以领先于 CPU 已收到的 ids'),
('结果提交等待 copy_done','append_host → EOS / 长度 / stop string','tool-call opener 可能设置状态锚点边界'),
('Detokenizer 生成安全增量','处理不完整字符与 stop 前缀保留','一个 token 不保证等于一个完整汉字'),
('取消在途请求先打 aborted 标志','等该 batch 排空再释放页、表和状态槽','防止 GPU 仍读取已分给新请求的内存')]),
}
def wrap(s,width=25):
    # Chinese width=2, ASCII width=1, retain readable technical names.
    out=[];line='';n=0
    for c in s:
        w=1 if ord(c)<128 else 2
        if n+w>width*2:out.append(line);line='';n=0
        line+=c;n+=w
    if line:out.append(line)
    return out
def text(x,y,s,size=18,color='#2b4437',width=25,bold=False):
    rows=wrap(s,width)
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">'+''.join(f'<tspan x="{x}" dy="{0 if i==0 else size*1.55}">{esc(t)}</tspan>' for i,t in enumerate(rows))+'</text>'
def frame(title,h):return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {h}" role="img"><title>{esc(title)}</title><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#659277"/></marker></defs><rect width="1000" height="{h}" fill="#faf9f2"/><g font-family="Microsoft YaHei,Noto Sans SC,system-ui,sans-serif">{text(38,47,title,25,width=38,bold=True)}'''
def flow(title,rows):
    h=122+len(rows)*190;s=frame(title,h)
    s+=text(40,88,'左列：处理；右列：本步交出的数据与状态。箭头沿同一条主线向下。',16,width=55,color='#6c7867')
    for i,(title,detail,state) in enumerate(rows):
        y=115+i*190
        s+=f'<rect x="38" y="{y}" width="495" height="145" rx="8" fill="#eaf0e1" stroke="#c5d2bb"/><rect x="570" y="{y}" width="390" height="145" rx="8" fill="#fffefa" stroke="#c5d2bb"/>'
        s+=text(56,y+33,f'{i+1:02}  {title}',20,width=23,bold=True)+text(57,y+78,detail,18,width=23)
        s+=text(590,y+35,'交接账本',14,color='#76816a')+text(590,y+73,state,18,width=18)
        s+=f'<path d="M535 {y+72}H567" stroke="#659277" stroke-width="2" marker-end="url(#arrow)"/>'
        if i+1<len(rows):s+=f'<path d="M765 {y+145}V{y+167}H280V{y+187}" fill="none" stroke="#659277" stroke-width="2" marker-end="url(#arrow)"/>'
    return s+'</g></svg>'
def timeline():
    title='Prefill 双缓冲：必须等读完，才能覆盖同一缓冲';s=frame(title,610)
    s+=text(40,90,'假设每层搬运 2 ms、计算 3 ms，共 4 层；只是时间模型。',18,width=48)
    x0=180;scale=49
    for t in range(15):
        x=x0+t*scale;s+=f'<path d="M{x} 130V465" stroke="#e1e4d9"/>'+text(x-4,496,str(t),14)
    for y,label in [(170,'H2D 拷贝流'),(280,'GPU 计算流')]:s+=text(28,y+30,label,18,width=8,bold=True)
    from_data=[(0,2,2,5),(2,4,5,8),(5,7,8,11),(8,10,11,14)]
    colors=['#b8d0ad','#edd39c']
    for l,(a,b,c,d) in enumerate(from_data):
        for lo,hi,y in [(a,b,160),(c,d,270)]:
            s+=f'<rect x="{x0+lo*scale}" y="{y}" width="{(hi-lo)*scale-3}" height="68" rx="5" fill="{colors[l%2]}" stroke="#a8b69f"/>'+text(x0+lo*scale+9,y+28,f'L{l} / B{l%2}',16,width=9)
        s+=f'<path d="M{x0+b*scale-10} 230V260H{x0+c*scale+8}" stroke="#659277" fill="none" stroke-width="2" marker-end="url(#arrow)"/>'
    s+=text(42,393,'B0 在 L0 的计算于 5 ms 结束后，才能搬 L2；B1 同理。',19,width=52)
    s+=text(42,435,'串行：4×(2+3)=20 ms；本时间线：14 ms（含起始加载与末层计算）。',19,width=52)
    s+=text(42,555,'源码关联：prefetch_prefill_layer / wait_prefill_layer / release_prefill_layer；ready 与 release 事件表达依赖。',17,width=57)
    return s+'</g></svg>'
FIGS['prefill']=('Prefill 双缓冲时间线：读完再覆盖',None)
def build(root):
    p=root/'figures';p.mkdir(exist_ok=True)
    for k,(title,rows) in FIGS.items():(p/(k+'.svg')).write_text(timeline() if k=='prefill' else flow(title,rows),encoding='utf-8')
