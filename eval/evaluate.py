"""创游助手 · 自动评测脚本。

对 6 项量化指标中的可自动测量项进行跑批，输出评测报告 JSON。
用法：python eval/evaluate.py  （在仓库根目录运行）
"""
import sys, os, json, time, shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.engine import GameForgeEngine

# 24 个评测任务卡（节选核心，可扩充）
TASKS = [
    {"id": "T01", "type": "generate", "text": "帮我做一个史莱姆勇者横版闯关游戏"},
    {"id": "T02", "type": "edit", "text": "把主角改成粉色"},
    {"id": "T03", "type": "edit", "text": "把主角改成蓝色"},
    {"id": "T04", "type": "edit", "text": "史莱姆速度调快"},
    {"id": "T05", "type": "edit", "text": "史莱姆速度调慢"},
    {"id": "T06", "type": "edit", "text": "主角跳得更高"},
    {"id": "T07", "type": "edit", "text": "把场景改成夜晚星空"},
    {"id": "T08", "type": "edit", "text": "把场景改回白天"},
    {"id": "T09", "type": "edit", "text": "增加金色史莱姆"},
    {"id": "T10", "type": "edit", "text": "击败史莱姆得分翻倍"},
    {"id": "T11", "type": "edit", "text": "增加初始生命"},
    {"id": "T12", "type": "recall", "text": "我之前提过哪些要求？"},
    {"id": "T13", "type": "recall", "text": "刚才说了什么？"},
    {"id": "T14", "type": "recall", "text": "我提过颜色的要求吗？"},
    {"id": "T15", "type": "rollback", "text": "回滚到上一版本"},
    {"id": "T16", "type": "generate", "text": "做一个轻松休闲的闯关小游戏"},
    {"id": "T17", "type": "edit", "text": "主角改成紫色"},
    {"id": "T18", "type": "edit", "text": "主角改成红色"},
    {"id": "T19", "type": "edit", "text": "史莱姆改成金色"},
    {"id": "T20", "type": "edit", "text": "让主角跑得更快"},
    {"id": "T21", "type": "generate", "text": "重新开始一个史莱姆勇者游戏"},
    {"id": "T22", "type": "edit", "text": "暮色氛围，主角橙色"},
    {"id": "T23", "type": "recall", "text": "列出所有要求"},
    {"id": "T24", "type": "rollback", "text": "回到最初的版本"},
]


def run():
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_eval_run")
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root, exist_ok=True)
    eng = GameForgeEngine(root)

    gen_ok = gen_total = 0
    latencies = []
    healths = []
    for t in TASKS:
        t0 = time.time()
        r = eng.run(t["text"])
        latencies.append((time.time() - t0) * 1000)
        if r.get("type") == "generate":
            gen_total += 1
            if r.get("ok") and r.get("report", {}).get("health", 0) >= 80:
                gen_ok += 1
            healths.append(r.get("report", {}).get("health", 0))

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0
    st = eng.status()

    report = {
        "任务数": len(TASKS),
        "生成成功率": {"值": round(gen_ok / gen_total, 3) if gen_total else 1.0,
                    "测量": "自检健康分≥80 判定成功"},
        "平均健康分": round(sum(healths) / len(healths), 1) if healths else 100,
        "P95延迟ms": round(p95, 1),
        "回滚一致性": {"值": 1.0 if st["chain_verified"] else 0.0, "测量": "哈希链完整校验"},
        "需求召回": {"入库数": st["requirements"], "测量": "需求账本条数"},
        "哈希链完整": st["chain_verified"],
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    shutil.rmtree(root, ignore_errors=True)
    return report


if __name__ == "__main__":
    run()
