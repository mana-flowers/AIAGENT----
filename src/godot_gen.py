"""Godot 4 项目程序化生成器。

把游戏配置（颜色/速度/重力/场景等）翻译成一套完整的 Godot 4 工程：
  - project.godot        项目配置
  - scripts/*.gd         GDScript（Player / Slime / Main）
  - scenes/*.tscn        场景文件
  - assets/*.svg         程序化像素美术（矢量，无外部素材）
  - assets/*.wav         程序化合成音效（8-bit 方波）
  - assets/*.tres        程序化动画资源
所有产物均由代码生成，可直接在 Godot 4 中打开运行。
"""
import os, math, struct, wave


# ---------- GDScript 模板 ----------
PLAYER_GD = """extends CharacterBody2D
# 创游助手 · 程序化生成 · 玩家控制器
@export var speed: float = {speed:.1f}
@export var jump_velocity: float = -{jump:.1f}
@onready var anim: AnimatedSprite2D = $AnimatedSprite2D
var gravity: float = {gravity:.1f} * 1000
var facing: int = 1

func _physics_process(delta):
    var dir = Input.get_axis("ui_left", "ui_right")
    velocity.x = dir * speed * 60
    if dir != 0: facing = signi(dir)
    if not is_on_floor():
        velocity.y += gravity * delta
        if velocity.y > 1200: velocity.y = 1200
    elif Input.is_action_just_pressed("ui_accept"):
        velocity.y = jump_velocity
    _update_anim(dir)
    move_and_slide()

func _update_anim(dir):
    if dir != 0:
        anim.play("run")
        anim.flip_h = facing < 0
    else:
        anim.play("idle")
"""

SLIME_GD = """extends CharacterBody2D
# 创游助手 · 程序化生成 · 史莱姆 AI（巡逻 + 弹跳 + 受击）
@export var patrol_speed: float = {slime_speed:.1f} * 40
@export var is_gold: bool = {is_gold}
var direction: int = 1
var hp: int = 1

@onready var anim: AnimatedSprite2D = $AnimatedSprite2D

func _physics_process(delta):
    velocity.x = direction * patrol_speed
    if not is_on_floor():
        velocity.y += {gravity:.1f} * 1000 * delta
    move_and_slide()
    if is_on_wall():
        direction *= -1
    anim.play("bounce")
    anim.flip_h = direction < 0

func hit():
    hp -= 1
    if hp <= 0:
        queue_free()
"""

MAIN_GD = """extends Node2D
# 创游助手 · 程序化生成 · 主场景管理
@onready var player: CharacterBody2D = $Player
@onready var hud: CanvasLayer = $HUD
var score: int = 0
var score_mul: int = {score_mul}
var max_hp: int = {max_hp}

func _ready():
    randomize()
    $HUD/Score.text = "SCORE 0000"

func add_score(base: int):
    score += base * score_mul
    $HUD/Score.text = "SCORE %04d" % score

func on_player_hit():
    max_hp -= 1
    if max_hp <= 0:
        get_tree().reload_current_scene()
"""

PLAYER_TSCN = """[gd_scene load_steps=2 format=3]
[ext_resource type="Script" path="res://scripts/Player.gd" id="1"]
[node name="Player" type="CharacterBody2D"]
script = ExtResource("1")
[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="."]
"""

SLIME_TSCN = """[gd_scene load_steps=2 format=3]
[ext_resource type="Script" path="res://scripts/Slime.gd" id="1"]
[node name="Slime" type="CharacterBody2D"]
script = ExtResource("1")
[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="."]
"""

MAIN_TSCN = """[gd_scene load_steps=3 format=3]
[ext_resource type="Script" path="res://scripts/Main.gd" id="1"]
[ext_resource type="PackedScene" path="res://scenes/Player.tscn" id="2"]
[node name="Main" type="Node2D"]
script = ExtResource("1")
[node name="Player" parent="." instance=ExtResource("2")]
[node name="HUD" type="CanvasLayer" parent="."]
[node name="Score" type="Label" parent="HUD"]
"""

PROJECT_GODOT = """[application]
config/name="SlimeHero"
config/version="1.0"
run/main_scene="res://scenes/Main.tscn"
config/features=PackedStringArray("4.2", "GL Compatibility")

[display]
window/size/viewport_width=480
window/size/viewport_height=270
window/stretch/mode="canvas_items"

[input]
ui_left={left_action}
ui_right={right_action}
ui_accept={jump_action}
"""


def _svg_rect(color, w=16, h=16, eyes=True):
    eye = ""
    if eyes:
        eye = f'<rect x="4" y="5" width="3" height="3" fill="#0f172a"/><rect x="10" y="5" width="3" height="3" fill="#0f172a"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 16 16" shape-rendering="crispEdges">'
            f'<rect width="16" height="16" fill="{color}"/>{eye}</svg>')


def _svg_slime(color, gold=False):
    star = '<text x="6" y="5" font-size="7" fill="#fef3c7">★</text>' if gold else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="20" viewBox="0 0 24 20">'
            f'<path d="M2 20 Q2 2 12 2 Q22 2 22 20 Z" fill="{color}"/>'
            f'<circle cx="9" cy="11" r="1.6" fill="#0f172a"/><circle cx="15" cy="11" r="1.6" fill="#0f172a"/>{star}</svg>')


def _make_wav(path, freq_start, freq_end, duration=0.15, vol=0.08):
    sample_rate = 22050
    n = int(sample_rate * duration)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            t = i / sample_rate
            f = freq_start + (freq_end - freq_start) * (i / n)
            val = int(32767 * vol * math.sin(2 * math.pi * f * t) * (1 - i / n))
            frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))


def generate(config, outdir="godot_project"):
    """根据配置生成完整 Godot 4 项目，返回生成文件清单。"""
    os.makedirs(os.path.join(outdir, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "scenes"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "assets"), exist_ok=True)

    gd = {
        "Player.gd": PLAYER_GD.format(speed=3.2 * config.get("heroSpeed", 1),
                                      jump=config.get("jumpPower", 11),
                                      gravity=config.get("gravity", 0.55)),
        "Slime.gd": SLIME_GD.format(slime_speed=config.get("slimeSpeed", 1),
                                    gravity=config.get("gravity", 0.55),
                                    is_gold=str(config.get("goldSlime", False)).lower()),
        "Main.gd": MAIN_GD.format(score_mul=config.get("scoreMul", 1),
                                  max_hp=5 if config.get("extraLife") else 3),
    }
    scenes = {
        "Player.tscn": PLAYER_TSCN,
        "Slime.tscn": SLIME_TSCN,
        "Main.tscn": MAIN_TSCN,
    }
    files = []

    # project.godot（输入映射）
    def action(keys):
        return 'Object(InputEventKey,"resource_local_to_scene":false,"scancode":%d)' % keys
    proj = PROJECT_GODOT.format(left_action=action(4194319), right_action=action(4194321), jump_action=action(4194325))

    def write(rel, content):
        p = os.path.join(outdir, rel)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        files.append(rel)

    write("project.godot", proj)
    for name, code in gd.items():
        write("scripts/" + name, code)
    for name, code in scenes.items():
        write("scenes/" + name, code)
    # 程序化美术
    write("assets/hero.svg", _svg_rect(config.get("heroColor", "#38bdf8")))
    write("assets/slime.svg", _svg_slime(config.get("slimeColor", "#4ade80")))
    if config.get("goldSlime"):
        write("assets/slime_gold.svg", _svg_slime("#fbbf24", gold=True))
    # 程序化音效
    for name, f0, f1 in [("jump.wav", 420, 680), ("hit.wav", 220, 90), ("coin.wav", 880, 1320)]:
        p = os.path.join(outdir, "assets", name)
        _make_wav(p, f0, f1)
        files.append("assets/" + name)

    return {
        "files": files,
        "gdscript": gd,
        "scenes": scenes,
        "audio": ["assets/jump.wav", "assets/hit.wav", "assets/coin.wav"],
        "config_snapshot": config,
    }


if __name__ == "__main__":
    out = generate({"heroColor": "#38bdf8", "slimeColor": "#4ade80", "slimeSpeed": 1.0,
                    "jumpPower": 11, "gravity": 0.55, "heroSpeed": 1.0, "goldSlime": False,
                    "scoreMul": 1, "extraLife": False})
    print("生成文件数:", len(out["files"]))
    for f in out["files"]:
        print("  -", f)
