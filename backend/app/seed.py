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
    finally:
        db.close()
