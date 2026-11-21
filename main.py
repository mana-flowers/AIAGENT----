"""创游助手 GameForge — 一键启动入口。

用法：
  python main.py           启动 API 服务（默认 127.0.0.1:8765）
  python main.py --selftest  运行内核自检（不启动服务）
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def selftest():
    import shutil
    from src.engine import GameForgeEngine
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest")
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root, exist_ok=True)
    e = GameForgeEngine(root)

    print("=" * 56)
    print("创游助手 · 内核自检")
    print("=" * 56)

    r1 = e.run("帮我做一个史莱姆勇者横版闯关游戏")
    print("① 首次生成:", "OK" if r1["ok"] and r1["type"] == "generate" else "FAIL",
          "| 步骤", len(r1["steps"]), "| 文件", len(r1.get("generated_files", [])),
          "| 健康分", r1.get("report", {}).get("health"))

    r2 = e.run("把主角改成粉色，史莱姆速度调快")
    print("② 意见修改:", "OK" if r2.get("config", {}).get("heroColor") == "#f472b6" else "FAIL",
          "| 主角色", r2.get("config", {}).get("heroColor"),
          "| 史莱姆速度", r2.get("config", {}).get("slimeSpeed"))

    r3 = e.run("增加金色史莱姆，击败后得分翻倍")
    print("③ 玩法增强:", "OK" if r3.get("config", {}).get("goldSlime") else "FAIL",
          "| goldSlime", r3.get("config", {}).get("goldSlime"),
          "| scoreMul", r3.get("config", {}).get("scoreMul"))

    r4 = e.run("我之前提过哪些要求？")
    print("④ 记忆调用:", "OK" if r4.get("type") == "recall" and len(r4.get("recall", [])) >= 3 else "FAIL",
          "| 召回", len(r4.get("recall", [])) if "recall" in r4 else 0, "条")

    st = e.status()
    rb = e.rollback(1)
    print("⑤ 版本回滚:", "OK" if rb["ok"] else "FAIL",
          "| 回滚后主角色", rb["config"]["heroColor"])

    print("-" * 56)
    print("需求数", st["requirements"], "| 事务数", st["transactions"],
          "| 快照数", st["snapshots"], "| 哈希链完整", st["chain_verified"])
    print("生成目录:", os.path.join(root, "godot_project"))
    shutil.rmtree(root, ignore_errors=True)
    print("=" * 56)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        from src.server import serve
        serve(os.path.dirname(os.path.abspath(__file__)))
