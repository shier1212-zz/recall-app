"""首次启动注入演示数据（幂等：已有数据则跳过）。"""
from app import models
from app.database import SessionLocal


def ensure_seed() -> None:
    db = SessionLocal()
    try:
        # 分类 + 错题：仅在初次（无分类数据）时录入
        if db.query(models.Category).count() == 0:
            cats = [
                models.Category(name="数学", color="#3B82F6"),
                models.Category(name="物理", color="#AF52DE"),
                models.Category(name="英语", color="#FF2D55"),
                models.Category(name="化学", color="#10B981"),
            ]
            db.add_all(cats)
            db.flush()

            samples = [
                models.Mistake(
                    category_id=cats[0].id, subject="数学",
                    content="已知函数 f(x)=x³−3x，求其在 x=1 处的切线方程，并判断单调性。",
                    knowledge_points=["导数", "切线", "单调性"], source="期中月考",
                    review_count=3, reviewed=True,
                    ai_analysis="f'(x)=3x²−3，f'(1)=0 为斜率；f(1)=−2，故切线 y=−2。令 f'(x)=0 得 x=±1。",
                ),
                models.Mistake(
                    category_id=cats[1].id, subject="物理",
                    content="光滑水平面上物体受恒力 F 作用，质量 m，求 t 秒后的位移与速度。",
                    knowledge_points=["牛顿第二定律", "匀加速直线运动"], source="课堂练习",
                    review_count=1, reviewed=False,
                    ai_analysis="a=F/m；v=Ft/m；x=Ft²/2m。注意初速度为 0。",
                ),
                models.Mistake(
                    category_id=cats[2].id, subject="英语",
                    content="The teacher insisted that he ___ (go) to school on time.",
                    knowledge_points=["虚拟语气", "insist"], source="英语周测",
                    review_count=5, reviewed=True,
                    ai_analysis="填 (should) go。insist 表“坚持要求”时从句用 (should)+动词原形。",
                ),
                models.Mistake(
                    category_id=cats[3].id, subject="化学",
                    content="用 0.1mol/L NaOH 滴定 20.00mL 未知浓度 HCl，终点耗碱 20.00mL，求 HCl 浓度。",
                    knowledge_points=["酸碱中和滴定"], source="实验报告",
                    review_count=0, reviewed=False,
                    ai_analysis="c(HCl)=0.1×20.00/20.00=0.1mol/L。",
                ),
            ]
            db.add_all(samples)
            db.commit()

        # 示例对话：仅当无会话时补充（独立幂等，避免已 seed 过分类的库始终缺会话）
        if db.query(models.Conversation).count() == 0:
            conv = models.Conversation(title="导数切线问题求解")
            db.add(conv)
            db.flush()
            db.add_all([
                models.ChatMessage(conversation_id=conv.id, role="user", content="这道导数题在 x=1 处切线怎么求？"),
                models.ChatMessage(conversation_id=conv.id, role="assistant", content="先求导 f'(x)=3x²−3，代入 x=1 得斜率 0；f(1)=−2，故切线 y=−2。需要变式题巩固吗？"),
            ])
            db.commit()

        # 示例答题圈帖子（仅首次；同标题会跳过，方便重试用）
        if db.query(models.CommunityPost).count() == 0:
            sample_posts = [
                models.CommunityPost(
                    title="【数学·圆锥曲线】求大神解析：椭圆离心率的快速算法",
                    summary="已知椭圆 a=2b，求离心率 e。一分钟内出答案的技巧有哪些？",
                    full_text="设椭圆方程 x²/a²+y²/b²=1 (a>b>0)，若长轴是短轴的 2 倍，即 a=2b，求离心率 e。\n提示：e = c/a = √(1 - b²/a²)。",
                    solution="核心思路：\n1. 由 a=2b 代入 b = a/2\n2. e = √(1 - (a/2)²/a²) = √(1 - 1/4) = √(3/4) = √3 / 2\n\n更快的方式：记忆公式 e² = 1 - (b/a)² = 1 - (1/2)² = 3/4，直接出答案。",
                    subject="数学",
                    author_name="圆锥曲线小白",
                    author_color="#5E5CE6",
                    view_count=42, like_count=8, share_count=2,
                ),
                models.CommunityPost(
                    title="【物理·电磁感应】导体棒切割磁感线的「右手定则」我一直用反，求记忆口诀",
                    summary="闭合回路中导体棒 ab 向右运动，磁感线垂直纸面向里，感应电流方向到底是 a→b 还是 b→a？",
                    full_text="一道选择题：水平面上有 U 形导轨，导体棒 ab 横放在导轨上，匀强磁场 B 垂直纸面向里。当 ab 向右匀速运动时，回路中感应电流方向？",
                    solution="右手定则口诀（更易记）：\n• 让磁感线「穿过」你的右手手心（手心朝向 N 极方向）\n• 拇指指向导体运动方向 v\n• 四指指向就是感应电流方向（在导体内部）\n\n这道题：手心朝里（B 向里指向你手心）、拇指指向右 → 四指在 ab 棒里指向上，即 a→b。",
                    subject="物理",
                    author_name="电磁感应苦手",
                    author_color="#FF9F0A",
                    view_count=128, like_count=24, share_count=7,
                ),
                models.CommunityPost(
                    title="【英语·虚拟语气】insist / suggest / demand 后到底用 should 还是动词原形？",
                    summary="虚拟语气这些「坚持/建议/要求」类动词后面到底怎么接，一直搞混，求一份对照表。",
                    full_text="下面三道题怎么填？\n1. The teacher insisted that he ___ (go) to school on time.\n2. I suggest that he ___ (read) the book again.\n3. She demanded that the door ___ (open) immediately.",
                    solution="结论：这三个词后都接 (should) + 动词原形，「should」通常省略。\n\n记忆要点：\n• insist / persist / demand / require / request / order / command / desire → 从句用 (should)+V原\n• suggest / propose / recommend / advise → 同样\n• 仅当这些词表「坚持认为」「暗示」时（I insist that he is innocent）是真实语气，才用正常时态。",
                    subject="英语",
                    author_name="虚拟语气收容所",
                    author_color="#FF453A",
                    view_count=256, like_count=51, share_count=14,
                ),
            ]
            db.add_all(sample_posts)
            db.flush()
            # 给第一条帖子加几条示例评论
            post = sample_posts[0]
            db.add_all([
                models.CommunityComment(
                    post_id=post.id, author_name="数学课代表",
                    author_color="#34C759",
                    content="感谢分享！记忆 e²=1-(b/a)² 这个公式真的太方便了，秒出答案。",
                ),
                models.CommunityComment(
                    post_id=post.id, author_name="圆锥曲线小白",
                    author_color="#5E5CE6",
                    content="@数学课代表 是的，这类公式推到做题速度真的差很多！",
                ),
            ])
            db.commit()
    finally:
        db.close()
