"""主编排器 Orchestrator — 感知→规划→记忆→工具→执行闭环。

 Master 编排四个 Worker（规划/代码/美术/质检），串联需求账本、事务链、
 快照回滚与 Godot 生成器。默认 mock 模式保证演示稳定，可切换真实 LLM。
"""
import os, json, copy, time
from .memory import RequirementLedger, TransactionChain, SnapshotStore
from .validator import SelfChecker
from . import godot_gen

DEFAULT_CONFIG = {
    "heroColor": "#38bdf8", "slimeColor": "#4ade80", "slimeSpeed": 1.0,
    "heroSpeed": 1.0, "gravity": 0.55, "jumpPower": 11, "bg": "day",
    "goldSlime": False, "extraLife": False, "scoreMul": 1,
}

COLOR_WORDS = {
    "蓝": "#38bdf8", "蓝色": "#38bdf8", "粉": "#f472b6", "粉色": "#f472b6",
    "红": "#f87171", "红色": "#f87171", "紫": "#a855f7", "紫色": "#a855f7",
    "绿": "#4ade80", "绿色": "#4ade80", "金": "#fbbf24", "金色": "#fbbf24",
    "橙": "#fb923c", "橙色": "#fb923c", "青": "#22d3ee", "青色": "#22d3ee",
}


class IntentParser:
    """感知层：把自然语言需求解析为配置变更。真实模式可替换为 LLM。"""

    def parse(self, text, config):
        t = text.lower()
        c = copy.deepcopy(config)
        ops = []
        # 颜色
        for who, key in [("主角", "heroColor"), ("史莱姆", "slimeColor")]:
            if who in t:
                for word, hexv in COLOR_WORDS.items():
                    if word in t:
                        c[key] = hexv
                        ops.append(f"{who}配色→{word}")
                        break
        # 速度
        if "快" in t or "加速" in t:
            key = "slimeSpeed" if "史莱姆" in t else "heroSpeed"
            c[key] = 1.8 if key == "slimeSpeed" else 1.6
            ops.append(("史莱姆" if key == "slimeSpeed" else "主角") + "速度提升")
        if "慢" in t or "减速" in t:
            key = "slimeSpeed" if "史莱姆" in t else "heroSpeed"
            c[key] = 0.5
            ops.append("速度降低")
        # 跳跃 / 场景 / 玩法
        if "跳" in t and ("高" in t or "力" in t):
            c["jumpPower"] = 14; ops.append("跳跃力增强")
        if any(w in t for w in ["夜晚", "黑夜", "星空", "夜间"]):
            c["bg"] = "night"; ops.append("场景→夜晚")
        if "白天" in t or "晴天" in t:
            c["bg"] = "day"; ops.append("场景→白昼")
        if "金色史莱姆" in t or ("加分" in t and "翻倍" in t):
            c["goldSlime"] = True; c["scoreMul"] = 2; ops.append("新增金色史莱姆")
        if "生命" in t or "三条命" in t or "加血" in t:
            c["extraLife"] = True; ops.append("初始生命+2")
        is_query = any(w in t for w in ["之前", "刚才", "提过", "哪些要求", "什么要求", "记住"])
        if not ops and not is_query:
            ops.append("保持玩法，微调视觉表现")
        return {"config": c, "ops": ops, "is_query": is_query}


class GameForgeEngine:
    def __init__(self, root="."):
        self.root = os.path.abspath(root)
        st = os.path.join(self.root, "state")
        self.ledger = RequirementLedger(os.path.join(st, "requirements.json"))
        self.chain = TransactionChain(os.path.join(st, "transactions.json"))
        self.snaps = SnapshotStore(os.path.join(st, "snapshots.json"))
        self.checker = SelfChecker()
        self.parser = IntentParser()
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.godot_dir = os.path.join(self.root, "godot_project")
        # 初始快照
        if not self.snaps.items:
            self.snaps.save(self.config, "v1 · 初始版本", "程序化生成史莱姆勇者基础版")
            self.chain.append("init", "初始化项目与需求账本")

    # ---------- 工具集（被 Agent 调用） ----------
    def tool_memory_recall(self, keyword=None):
        reqs = self.ledger.search(keyword) if keyword else self.ledger.all()
        return [{"id": r["id"], "text": r["text"], "time": r["time"]} for r in reqs]

    def tool_edit_config(self, new_config, ops):
        self.chain.append("edit_config", "变更: " + "、".join(ops), "coder")
        return new_config

    def tool_gen_godot(self, config):
        result = godot_gen.generate(config, self.godot_dir)
        self.chain.append("gen_godot", f"生成 Godot 项目 {len(result['files'])} 个文件", "artist")
        return result

    def tool_selfcheck(self, config, gen):
        report = self.checker.check(config, gen["gdscript"], gen["scenes"], gen["audio"])
        self.chain.append("selfcheck", f"健康分 {report['health']}，修复 {len(report['fixed'])} 项", "qa")
        return report

    def tool_snapshot(self, config, label, desc):
        snap = self.snaps.save(config, label, desc)
        self.chain.append("snapshot", f"写入快照 {snap['addr']}", "orchestrator")
        return snap

    # ---------- 主流程 ----------
    def run(self, requirement):
        """接收玩家意见，执行完整多智能体协作，返回结构化 trace。"""
        trace = {"requirement": requirement, "steps": [], "ok": True}

        def step(agent, action, detail):
            trace["steps"].append({"agent": agent, "action": action, "detail": detail,
                                   "time": time.strftime("%H:%M:%S")})

        # 记忆层：全量留存
        req = self.ledger.add(requirement)
        step("memory", "需求入库", f"{req['id']} 已写入需求账本（累计 {len(self.ledger)} 条）")

        # 感知层：意图解析
        intent = self.parser.parse(requirement, self.config)
        step("planner", "意图解析", f"识别 {len(intent['ops'])} 项变更：" + "、".join(intent["ops"]))

        # 记忆调用类：直接返回检索结果，不触发生成
        if intent["is_query"] and len(self.ledger) > 1:
            reqs = self.tool_memory_recall()
            step("planner", "记忆调用", f"检索需求账本，命中 {len(reqs)} 条历史要求")
            trace["recall"] = reqs
            trace["type"] = "recall"
            return trace

        # 规划层
        step("planner", "任务拆解", "修改脚本→重绘素材→重合成音效→触发自检")
        # 代码层
        new_config = self.tool_edit_config(intent["config"], intent["ops"])
        step("coder", "GDScript 热更新", "Player.gd / Slime.gd / Main.gd 参数已注入")
        # 美术层（程序化生成）
        gen = self.tool_gen_godot(new_config)
        step("artist", "程序化素材", f"生成 {len(gen['files'])} 文件（脚本/场景/SVG/WAV）")
        # 质检层
        report = self.tool_selfcheck(new_config, gen)
        step("qa", "自检自查", f"健康分 {report['health']}，自动修复 {len(report['fixed'])} 项")
        # 提交层
        self.config = report.get("config", new_config)
        snap = self.tool_snapshot(self.config, f"v{len(self.snaps.items)+1} · {intent['ops'][0]}",
                                  "、".join(intent["ops"]))
        step("orchestrator", "版本快照", f"快照 {snap['addr']} 已写入事务链")
        step("orchestrator", "生成完成", "游戏已热更新，可试玩 / 可回滚")

        trace.update({
            "type": "generate", "config": self.config, "report": report,
            "snapshot": snap, "generated_files": gen["files"],
            "chain_verified": self.chain.verify(),
        })
        return trace

    def rollback(self, version):
        cfg = self.snaps.rollback(version)
        if not cfg:
            return {"ok": False, "error": f"版本 v{version} 不存在"}
        self.config = cfg
        gen = self.tool_gen_godot(cfg)
        self.chain.append("rollback", f"回滚到 v{version}", "orchestrator")
        return {"ok": True, "version": version, "config": cfg,
                "generated_files": gen["files"], "time": time.strftime("%H:%M:%S")}

    def status(self):
        return {
            "ok": True,
            "requirements": len(self.ledger),
            "transactions": len(self.chain.items),
            "snapshots": len(self.snaps.items),
            "chain_verified": self.chain.verify(),
            "current_config": self.config,
            "versions": [{"version": s["version"], "label": s["label"], "addr": s["addr"],
                          "time": s["time"]} for s in self.snaps.items],
        }
