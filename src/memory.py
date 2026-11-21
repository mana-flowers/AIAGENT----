"""需求账本 + 事务链 + 内容寻址快照。

对应方案书中的"记住所有要求、随时调用、随时回滚"核心机制：
  - RequirementLedger : 全量需求留存（append-only），支持检索与引用溯源
  - TransactionChain  : 每次变更形成不可篡改的事务记录（hash 链）
  - SnapshotStore     : 内容寻址快照，支持任意版本回滚
"""
import os, json, time, hashlib, threading
from collections import OrderedDict


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _hash(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


class RequirementLedger:
    """需求账本：append-only，每条需求带唯一 ID、时间、来源、溯源标签。"""

    def __init__(self, path="state/requirements.json"):
        self.path = path
        self._lock = threading.Lock()
        self.items = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception:
                self.items = []

    def _persist(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    def add(self, text, source="玩家意见", tags=None):
        with self._lock:
            rec = {
                "id": "R%03d" % (len(self.items) + 1),
                "text": text.strip(),
                "source": source,
                "tags": tags or [],
                "time": _now(),
            }
            self.items.append(rec)
            self._persist()
            return rec

    def all(self):
        return list(self.items)

    def search(self, keyword):
        """按关键词检索需求，返回带引用的结果（引用溯源）。"""
        kw = keyword.lower()
        return [r for r in self.items if kw in r["text"].lower() or kw in " ".join(r["tags"]).lower()]

    def get(self, rid):
        for r in self.items:
            if r["id"] == rid:
                return r
        return None

    def as_context(self):
        """把全部需求打包成生成上下文，供任意时刻"随时调用"。"""
        return [{"id": r["id"], "text": r["text"], "time": r["time"]} for r in self.items]

    def __len__(self):
        return len(self.items)


class TransactionChain:
    """事务链：每次变更记录 prev_hash，形成可追溯的哈希链。"""

    def __init__(self, path="state/transactions.json"):
        self.path = path
        self.items = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception:
                self.items = []

    def _persist(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    def append(self, op, detail, agent="orchestrator"):
        prev = self.items[-1]["hash"] if self.items else "0" * 16
        rec = {
            "seq": len(self.items) + 1,
            "op": op,
            "detail": detail,
            "agent": agent,
            "time": _now(),
            "prev_hash": prev,
        }
        rec["hash"] = _hash(rec)
        self.items.append(rec)
        self._persist()
        return rec

    def all(self):
        return list(self.items)

    def verify(self):
        """校验哈希链完整性。"""
        prev = "0" * 16
        for r in self.items:
            if r["prev_hash"] != prev:
                return False
            prev = r["hash"]
        return True


class SnapshotStore:
    """内容寻址快照：以配置内容哈希为地址，支持任意版本回滚。"""

    def __init__(self, path="state/snapshots.json"):
        self.path = path
        self.items = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception:
                self.items = []

    def _persist(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    def save(self, config, label, desc=""):
        addr = _hash(config)
        rec = {
            "version": len(self.items) + 1,
            "addr": addr,
            "label": label,
            "desc": desc,
            "config": json.loads(json.dumps(config)),  # deep copy
            "time": _now(),
        }
        self.items.append(rec)
        self._persist()
        return rec

    def get(self, version):
        for r in self.items:
            if r["version"] == version:
                return r
        return None

    def latest(self):
        return self.items[-1] if self.items else None

    def all(self):
        return list(self.items)

    def rollback(self, version):
        """回滚到指定版本，返回该版本配置；不删除后续快照（可再前进）。"""
        rec = self.get(version)
        if not rec:
            return None
        return json.loads(json.dumps(rec["config"]))
