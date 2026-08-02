#!/usr/bin/env python3
"""
30x30 / 3x3 Zone 房間與通道地圖生成器 —— 引擎無關參考實作

目的：在寫 Godot / Unity 程式碼之前，先在純 Python 裡把演算法跑通、驗證連通性、
      調整密度參數。引擎端只需照著這份實作逐行移植，不必在引擎裡除錯演算法。

用法：
    python3 mapgen_reference.py            # 產生 1 張地圖並以 ASCII 印出
    python3 mapgen_reference.py --seed 42 --floor 12
    python3 mapgen_reference.py --stress 2000    # 壓力測試：驗證連通性與統計分佈

對應文件：docs/roguelike_mapgen.md（演算法說明與虛擬碼）
資料來源：docs/roguelike_data/items.json、monsters.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import deque
from dataclasses import dataclass, field

# ---------------------------------------------------------------- 常數

MAP_W, MAP_H = 30, 30
ZONE_COLS, ZONE_ROWS = 3, 3
ZONE_W, ZONE_H = MAP_W // ZONE_COLS, MAP_H // ZONE_ROWS   # 10 x 10

MARGIN = 1          # 區域內縮：保證相鄰區域的房間之間永遠有間隙可走通道
ROOM_MIN = 3        # 房間最小邊長
MIN_ROOMS = 6       # 至少要有幾個房間（其餘區域退化為通道交會點）
MAX_EMPTY_ZONES = 3
LOOP_CHANCE = 0.18  # 生成樹之外的額外環路機率
MAX_ATTEMPTS = 5

WALL, FLOOR, CORRIDOR = 0, 1, 2

RIGHT, LEFT, DOWN, UP = "R", "L", "D", "U"

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- 資料結構

@dataclass
class Zone:
    idx: int
    zx: int
    zy: int
    x0: int
    y0: int
    x1: int
    y1: int


@dataclass
class Room:
    zone: int
    x: int
    y: int
    w: int
    h: int
    doors: list = field(default_factory=list)

    @property
    def right(self) -> int:
        return self.x + self.w - 1

    @property
    def bottom(self) -> int:
        return self.y + self.h - 1

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x <= self.right and self.y <= y <= self.bottom


@dataclass
class Floor:
    tiles: list                       # tiles[y][x] -> WALL / FLOOR / CORRIDOR
    room_at: list                     # room_at[y][x] -> room zone index，通道為 -1
    rooms: dict                       # zone_idx -> Room
    junctions: dict                   # zone_idx -> (x, y)
    edges: list                       # [(zone_a, zone_b)]
    player_pos: tuple = (0, 0)
    stairs_down: tuple = (0, 0)
    stairs_up: tuple = (0, 0)
    items: dict = field(default_factory=dict)      # (x,y) -> item id
    golds: dict = field(default_factory=dict)      # (x,y) -> amount
    traps: dict = field(default_factory=dict)      # (x,y) -> trap id
    monsters: dict = field(default_factory=dict)   # (x,y) -> monster id
    shop_zone: int = -1

    def walkable(self, x: int, y: int) -> bool:
        return 0 <= x < MAP_W and 0 <= y < MAP_H and self.tiles[y][x] != WALL


# ---------------------------------------------------------------- Step 1-2：區域切割

def split_zones() -> list:
    """把 30x30 切成 3x3 = 9 個 10x10 的區域。"""
    zones = []
    for zy in range(ZONE_ROWS):
        for zx in range(ZONE_COLS):
            zones.append(Zone(
                idx=zy * ZONE_COLS + zx, zx=zx, zy=zy,
                x0=zx * ZONE_W, y0=zy * ZONE_H,
                x1=zx * ZONE_W + ZONE_W - 1,
                y1=zy * ZONE_H + ZONE_H - 1,
            ))
    return zones


# ---------------------------------------------------------------- Step 3：房間

def place_rooms(rng: random.Random, zones: list):
    """每個區域內縮 MARGIN 後隨機生成房間；被選為空的區域改放通道交會點。"""
    empty_count = rng.randint(0, MAX_EMPTY_ZONES)
    empty_count = min(empty_count, len(zones) - MIN_ROOMS)
    empty_idx = set(rng.sample([z.idx for z in zones], empty_count))

    rooms, junctions = {}, {}
    for z in zones:
        ux0, ux1 = z.x0 + MARGIN, z.x1 - MARGIN      # 可用範圍 8 格寬
        uy0, uy1 = z.y0 + MARGIN, z.y1 - MARGIN

        if z.idx in empty_idx:
            # 空區域仍是連通圖上的節點 —— 這是「所有房間必定可達」的關鍵
            junctions[z.idx] = (rng.randint(ux0 + 1, ux1 - 1),
                                rng.randint(uy0 + 1, uy1 - 1))
            continue

        max_w, max_h = ux1 - ux0 + 1, uy1 - uy0 + 1  # 8, 8
        w = rng.randint(ROOM_MIN, max_w - 1)         # 3..7，留 1 格給通道轉圜
        h = rng.randint(ROOM_MIN, max_h - 1)
        x = rng.randint(ux0, ux1 - w + 1)
        y = rng.randint(uy0, uy1 - h + 1)
        rooms[z.idx] = Room(zone=z.idx, x=x, y=y, w=w, h=h)

    return rooms, junctions


# ---------------------------------------------------------------- Step 4：連通圖

class UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.p[ra] = rb
        return True


def build_connection_graph(rng: random.Random, zones: list) -> list:
    """先取隨機生成樹保證全連通，再注入環路避免『死路 = 必死』。"""
    candidates = []
    for a in zones:
        for b in zones:
            if a.idx < b.idx and abs(a.zx - b.zx) + abs(a.zy - b.zy) == 1:
                candidates.append((a.idx, b.idx))

    rng.shuffle(candidates)
    uf = UnionFind(len(zones))
    tree, rest = [], []
    for e in candidates:
        (tree if uf.union(e[0], e[1]) else rest).append(e)

    assert len(tree) == len(zones) - 1, "9 節點的生成樹必有 8 條邊"

    extra = [e for e in rest if rng.random() < LOOP_CHANCE]
    return tree + extra


# ---------------------------------------------------------------- Step 5：通道

def node_port(rng: random.Random, rooms: dict, junctions: dict,
              zone_idx: int, side: str) -> tuple:
    """回傳該節點朝指定方向的出口座標（房間 → 牆外 1 格；交會點 → 自身）。"""
    if zone_idx in junctions:
        return junctions[zone_idx]
    r = rooms[zone_idx]
    if side == RIGHT:
        return (r.right + 1, rng.randint(r.y, r.bottom))
    if side == LEFT:
        return (r.x - 1, rng.randint(r.y, r.bottom))
    if side == DOWN:
        return (rng.randint(r.x, r.right), r.bottom + 1)
    return (rng.randint(r.x, r.right), r.y - 1)      # UP


def carve_h(tiles, x_a: int, x_b: int, y: int):
    for x in range(min(x_a, x_b), max(x_a, x_b) + 1):
        if tiles[y][x] == WALL:
            tiles[y][x] = CORRIDOR


def carve_v(tiles, y_a: int, y_b: int, x: int):
    for y in range(min(y_a, y_b), max(y_a, y_b) + 1):
        if tiles[y][x] == WALL:
            tiles[y][x] = CORRIDOR


def carve_corridors(rng, tiles, zones, rooms, junctions, edges):
    """Z 字形通道：出房間 → 走到轉折線 → 平移 → 進另一間房。"""
    for e in edges:
        za, zb = zones[e[0]], zones[e[1]]
        if za.zy == zb.zy:                                   # 水平連接
            left, right = (za, zb) if za.zx < zb.zx else (zb, za)
            pa = node_port(rng, rooms, junctions, left.idx, RIGHT)
            pb = node_port(rng, rooms, junctions, right.idx, LEFT)
            # MARGIN 保證 pa.x < pb.x，轉折線必定有合法位置
            mid_x = rng.randint(pa[0], pb[0])
            carve_h(tiles, pa[0], mid_x, pa[1])
            carve_v(tiles, pa[1], pb[1], mid_x)
            carve_h(tiles, mid_x, pb[0], pb[1])
            _register_door(rooms, left.idx, pa)
            _register_door(rooms, right.idx, pb)
        else:                                                # 垂直連接
            top, bottom = (za, zb) if za.zy < zb.zy else (zb, za)
            pa = node_port(rng, rooms, junctions, top.idx, DOWN)
            pb = node_port(rng, rooms, junctions, bottom.idx, UP)
            mid_y = rng.randint(pa[1], pb[1])
            carve_v(tiles, pa[1], mid_y, pa[0])
            carve_h(tiles, pa[0], pb[0], mid_y)
            carve_v(tiles, mid_y, pb[1], pb[0])
            _register_door(rooms, top.idx, pa)
            _register_door(rooms, bottom.idx, pb)


def _register_door(rooms: dict, zone_idx: int, pos: tuple):
    """記錄門口座標 —— 供 GDD §1.5『門口禁止斜向進出』規則使用。"""
    if zone_idx in rooms and pos not in rooms[zone_idx].doors:
        rooms[zone_idx].doors.append(pos)


# ---------------------------------------------------------------- Step 6：驗證

def flood_fill_4dir(tiles, start: tuple) -> set:
    """必須用 4 向！斜向切牆角在 GDD §1.5 被禁止，用 8 向驗證會放行實際走不通的圖。"""
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < MAP_W and 0 <= ny < MAP_H
                    and tiles[ny][nx] != WALL and (nx, ny) not in seen):
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def verify_connectivity(tiles) -> bool:
    walkable = [(x, y) for y in range(MAP_H) for x in range(MAP_W)
                if tiles[y][x] != WALL]
    if not walkable:
        return False
    return len(flood_fill_4dir(tiles, walkable[0])) == len(walkable)


# ---------------------------------------------------------------- Step 7：物件放置

def bfs_zone_distance(edges: list, start_zone: int) -> dict:
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    dist = {start_zone: 0}
    q = deque([start_zone])
    while q:
        z = q.popleft()
        for n in adj.get(z, []):
            if n not in dist:
                dist[n] = dist[z] + 1
                q.append(n)
    return dist


def _falloff(f: int, lo: int, hi: int, edge_ratio: float = 0.4) -> float:
    """出現表衰減：主場層段中央 1.0、邊界 edge_ratio、範圍外 0。"""
    if not (lo <= f <= hi):
        return 0.0
    if hi == lo:
        return 1.0
    center = (lo + hi) / 2.0
    t = abs(f - center) / ((hi - lo) / 2.0)
    return 1.0 - (1.0 - edge_ratio) * t


def _weighted_pick(rng: random.Random, entries: list):
    total = sum(w for _, w in entries)
    if total <= 0:
        return None
    r = rng.uniform(0, total)
    for obj, w in entries:
        r -= w
        if r <= 0:
            return obj
    return entries[-1][0]


def load_tables():
    with open(os.path.join(DATA_DIR, "items.json"), encoding="utf-8") as f:
        items = json.load(f)
    with open(os.path.join(DATA_DIR, "monsters.json"), encoding="utf-8") as f:
        monsters = json.load(f)
    flat_items = []
    for key in ("foods", "weapons", "shields", "herbs", "scrolls", "wands", "pots"):
        flat_items.extend(items[key])
    return flat_items, monsters["monsters"]


def place_objects(rng, floor: Floor, F: int, item_table, monster_table):
    rooms = list(floor.rooms.values())

    # 1. 出生點（上行樓梯同格）
    spawn_room = rng.choice(rooms)
    floor.player_pos = _rand_tile_in_room(rng, spawn_room)
    floor.stairs_up = floor.player_pos

    # 2. 下行樓梯：取區域圖上距出生區域最遠的前 3 個房間中隨機 —— 保證探索長度
    dist = bfs_zone_distance(floor.edges, spawn_room.zone)
    ranked = sorted(rooms, key=lambda r: -dist.get(r.zone, 0))
    candidates = [r for r in ranked if r.zone != spawn_room.zone][:3] or ranked[:1]
    stairs_room = rng.choice(candidates)
    floor.stairs_down = _rand_tile_in_room(rng, stairs_room, exclude={floor.player_pos})

    occupied = {floor.player_pos, floor.stairs_down}

    def free_tile(min_dist_from_player=0):
        for _ in range(200):
            x = rng.randrange(MAP_W)
            y = rng.randrange(MAP_H)
            if floor.tiles[y][x] == WALL or (x, y) in occupied:
                continue
            px, py = floor.player_pos
            if max(abs(x - px), abs(y - py)) < min_dist_from_player:
                continue
            occupied.add((x, y))
            return (x, y)
        return None

    # 3. 密度公式（GDD §4.2）
    n_items = rng.randint(3, 6) + F // 8
    n_gold = rng.randint(1, 3)
    n_traps = rng.randint(1, 2) + F // 5
    n_monsters = max(2, min(2 + F // 3, 12))

    item_pool = [(it, it["spawn_weight"] * _falloff(F, *it["floor_range"]))
                 for it in item_table]
    item_pool = [(o, w) for o, w in item_pool if w > 0]
    mon_pool = [(m, m["spawn_weight"] * _falloff(F, *m["floor_range"]))
                for m in monster_table]
    mon_pool = [(o, w) for o, w in mon_pool if w > 0]

    for _ in range(n_items):
        p = free_tile()
        pick = _weighted_pick(rng, item_pool)
        if p and pick:
            floor.items[p] = pick["id"]
    for _ in range(n_gold):
        p = free_tile()
        if p:
            floor.golds[p] = rng.randint(10, 40) * (1 + F // 3)
    for _ in range(n_traps):
        p = free_tile()
        if p:
            floor.traps[p] = "trap_generic"
    for _ in range(n_monsters):
        p = free_tile(min_dist_from_player=3)   # 絕不緊貼玩家生成
        pick = _weighted_pick(rng, mon_pool)
        if p and pick:
            floor.monsters[p] = pick["id"]

    # 4. 商店：必須恰有 1 個門口（GDD §4.3）
    if F >= 3 and rng.random() < 0.08:
        single_door = [r for r in rooms if len(r.doors) == 1
                       and not _room_has(floor, r, occupied_only=True)]
        if single_door:
            floor.shop_zone = rng.choice(single_door).zone


def _rand_tile_in_room(rng, room: Room, exclude: set = frozenset()) -> tuple:
    for _ in range(100):
        p = (rng.randint(room.x, room.right), rng.randint(room.y, room.bottom))
        if p not in exclude:
            return p
    return (room.x, room.y)


def _room_has(floor: Floor, room: Room, occupied_only=False) -> bool:
    return any(room.contains(*p) for p in
               (list(floor.traps) + [floor.stairs_down, floor.player_pos]))


# ---------------------------------------------------------------- 主流程

def try_generate(rng, F, item_table, monster_table):
    tiles = [[WALL] * MAP_W for _ in range(MAP_H)]
    zones = split_zones()
    rooms, junctions = place_rooms(rng, zones)

    for r in rooms.values():
        for y in range(r.y, r.bottom + 1):
            for x in range(r.x, r.right + 1):
                tiles[y][x] = FLOOR

    edges = build_connection_graph(rng, zones)
    carve_corridors(rng, tiles, zones, rooms, junctions, edges)

    if not verify_connectivity(tiles):
        return None

    room_at = [[-1] * MAP_W for _ in range(MAP_H)]
    for r in rooms.values():
        for y in range(r.y, r.bottom + 1):
            for x in range(r.x, r.right + 1):
                room_at[y][x] = r.zone

    floor = Floor(tiles=tiles, room_at=room_at, rooms=rooms,
                  junctions=junctions, edges=edges)
    place_objects(rng, floor, F, item_table, monster_table)

    # 最終保險：樓梯必須從出生點可達
    reach = flood_fill_4dir(tiles, floor.player_pos)
    if floor.stairs_down not in reach:
        return None
    return floor


def generate_floor(run_seed: int, floor_index: int) -> Floor:
    item_table, monster_table = load_tables()
    for attempt in range(MAX_ATTEMPTS):
        rng = random.Random(hash((run_seed, floor_index, attempt)) & 0xFFFFFFFF)
        floor = try_generate(rng, floor_index, item_table, monster_table)
        if floor is not None:
            return floor
    return _fallback_floor()


def _fallback_floor() -> Floor:
    """保底樓層：單一大房間。寧可無聊，也絕不讓玩家卡在無法通關的圖上。"""
    tiles = [[WALL] * MAP_W for _ in range(MAP_H)]
    for y in range(2, MAP_H - 2):
        for x in range(2, MAP_W - 2):
            tiles[y][x] = FLOOR
    room = Room(zone=0, x=2, y=2, w=MAP_W - 4, h=MAP_H - 4)
    room_at = [[0 if tiles[y][x] != WALL else -1 for x in range(MAP_W)]
               for y in range(MAP_H)]
    f = Floor(tiles=tiles, room_at=room_at, rooms={0: room},
              junctions={}, edges=[])
    f.player_pos = (3, 3)
    f.stairs_up = (3, 3)
    f.stairs_down = (MAP_W - 4, MAP_H - 4)
    return f


# ---------------------------------------------------------------- 輸出

GLYPH = {WALL: "#", FLOOR: ".", CORRIDOR: "+"}


def render(floor: Floor) -> str:
    grid = [[GLYPH[floor.tiles[y][x]] for x in range(MAP_W)] for y in range(MAP_H)]
    for (x, y) in floor.traps:
        grid[y][x] = "^"
    for (x, y) in floor.golds:
        grid[y][x] = "$"
    for (x, y) in floor.items:
        grid[y][x] = "!"
    for (x, y) in floor.monsters:
        grid[y][x] = "M"
    sx, sy = floor.stairs_down
    grid[sy][sx] = ">"
    px, py = floor.player_pos
    grid[py][px] = "@"
    lines = ["".join(row) for row in grid]
    zone_line = "  區域邊界： x = 10, 20 ／ y = 10, 20"
    return "\n".join(lines) + "\n" + zone_line


def stress_test(n: int):
    item_table, monster_table = load_tables()
    fails = 0
    room_counts, corridor_ratio, retries = [], [], 0
    for seed in range(n):
        floor = None
        for attempt in range(MAX_ATTEMPTS):
            rng = random.Random(hash((seed, 5, attempt)) & 0xFFFFFFFF)
            floor = try_generate(rng, 5, item_table, monster_table)
            if floor:
                retries += attempt
                break
        if floor is None:
            fails += 1
            continue
        room_counts.append(len(floor.rooms))
        walk = sum(1 for y in range(MAP_H) for x in range(MAP_W)
                   if floor.tiles[y][x] != WALL)
        corr = sum(1 for y in range(MAP_H) for x in range(MAP_W)
                   if floor.tiles[y][x] == CORRIDOR)
        corridor_ratio.append(corr / walk)
        assert verify_connectivity(floor.tiles), f"seed {seed} 連通性驗證失敗"
        assert floor.stairs_down in flood_fill_4dir(floor.tiles, floor.player_pos)

    print(f"樣本數        : {n}")
    print(f"生成失敗      : {fails}  ({fails / n:.3%})")
    print(f"重試次數合計  : {retries}")
    print(f"房間數        : min={min(room_counts)} max={max(room_counts)} "
          f"avg={sum(room_counts) / len(room_counts):.2f}")
    print(f"通道佔可走格  : avg={sum(corridor_ratio) / len(corridor_ratio):.1%}")
    print("連通性        : 全數通過（4 向 flood fill，含樓梯可達性）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260802)
    ap.add_argument("--floor", type=int, default=5)
    ap.add_argument("--stress", type=int, default=0)
    args = ap.parse_args()

    if args.stress:
        stress_test(args.stress)
        return

    floor = generate_floor(args.seed, args.floor)
    print(render(floor))
    print(f"\n  seed={args.seed} floor={args.floor}  "
          f"房間 {len(floor.rooms)} / 交會點 {len(floor.junctions)} / "
          f"通道邊 {len(floor.edges)}")
    print(f"  @ 出生點 {floor.player_pos}   > 下行樓梯 {floor.stairs_down}")
    print(f"  ! 道具 {len(floor.items)}  $ 金錢 {len(floor.golds)}  "
          f"^ 陷阱 {len(floor.traps)}  M 怪物 {len(floor.monsters)}")


if __name__ == "__main__":
    main()
