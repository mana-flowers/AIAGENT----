"""创游助手 GameForge — Agent 内核包。

模块划分：
  memory    需求账本 + 事务链 + 内容寻址快照（记忆、追溯、回滚）
  validator 自检自查规则引擎
  agents    多智能体（规划/代码/美术/质检）与工具集
  godot_gen Godot 4 项目程序化生成器（脚本/美术/音效/动画）
  engine    主编排器，串联感知-规划-记忆-工具-执行
  server    标准库 HTTP API（零依赖）
"""
__version__ = "1.0.0"
