#!/usr/bin/env python3
"""cover_outfit.py — 封面本人胸像的"衣柜": 每期挑一件不同的衣服, 生成 GPT 补全半身的完整 prompt。

  python3 scripts/cover_outfit.py --project 网球奖金金字塔          # 按季节随机挑一件(避开最近6期), 记入历史, 打印 prompt
  python3 scripts/cover_outfit.py --project X --pick navy-polo     # 用户点名/指定某件 (id 或中文关键字)
  python3 scripts/cover_outfit.py --list                            # 看衣柜 + 每件最近穿的日期
  python3 scripts/cover_outfit.py --project X --dry-run             # 只看不记
  python3 scripts/cover_outfit.py --project X --season winter       # 指定季节 (默认按当前月份)

衣柜: <skill>/assets/cover-wardrobe.json (公共; 条目 {"id": 英文短id, "zh": 写进 prompt 的中文描述, "tags": [spring/summer/autumn/winter + 自由标签]})。
季节按当月: 3-5 spring, 6-8 summer, 9-11 autumn, 12-2 winter; --season any 不过滤。
历史: $PERSONAL_ASSETS/cover_outfit_history.json (个人数据, 不入库), 记录 {date, project, id}。
同一项目重跑不会再换衣服 —— 已有记录时直接复用该项目的衣服 (重出图/补横版时保持一致); --renew 强制换。
"""
import argparse, datetime, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_cands = [os.environ.get("COVER_WARDROBE", ""), os.path.join(HERE, "..", "assets", "cover-wardrobe.json"),
          os.path.expanduser("~/.claude/skills/vertical-commentary-video/assets/cover-wardrobe.json")]
WARDROBE = next((c for c in _cands if c and os.path.exists(c)), _cands[-1])   # 脚本被 cp 到项目 build/ 时回退到 skill 目录
PA = os.environ.get("PERSONAL_ASSETS", "/Volumes/Storage/avatar-template/assets")
HISTORY = os.path.join(PA, "cover_outfit_history.json")
FACE_REF = os.environ.get("COVER_FACE_REF", os.path.join(PA, "cover_face_ref.jpg"))
AVOID_LAST = 6

PROMPT = ("以我附上的这张本人照片为准, 完全保留这张脸: 五官、发型、肤色、表情都不要改, 不要美化, 不要换成别人; "
          "补全成一张完整的上半身正面形象: 肩膀、双臂、腰部以上全部完整在画面里, 四周留出空白, "
          "双臂自然下垂或轻松交叉在胸前; 穿{outfit}; 纯白背景, 没有任何文字、logo或水印; 竖版3比4输出一张。")


def season_now():
    m = datetime.date.today().month
    return {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}[m]


def load_history():
    try:
        with open(HISTORY) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(h):
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "w") as f:
        json.dump(h, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="项目名 (记历史用; 同项目重跑复用同一件)")
    ap.add_argument("--pick", help="指定衣服: id 或中文关键字")
    ap.add_argument("--season", default="auto", help="spring/summer/autumn/winter/any, 默认按当月")
    ap.add_argument("--avoid-last", type=int, default=AVOID_LAST, help="避开最近 N 期穿过的 (默认 %(default)s)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="不写历史")
    ap.add_argument("--renew", action="store_true", help="同项目已有记录时也重新挑")
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()

    with open(WARDROBE) as f:
        outfits = json.load(f)["outfits"]
    by_id = {o["id"]: o for o in outfits}
    hist = load_history()
    last_worn = {}
    for e in hist:
        last_worn[e["id"]] = e["date"]

    if a.list:
        print(f"衣柜 {len(outfits)} 件 (历史: {HISTORY})")
        for o in outfits:
            print(f"  {o['id']:<18} {o['zh']:<32} {','.join(o['tags']):<32} 最近: {last_worn.get(o['id'], '—')}")
        return

    if not a.project and not a.pick:
        ap.error("需要 --project (或 --pick)")

    prev = next((e for e in reversed(hist) if e.get("project") == a.project), None) if a.project else None
    if prev and not a.renew and not a.pick and prev["id"] in by_id:
        o = by_id[prev["id"]]
        print(f"[cover_outfit] 项目「{a.project}」已记录衣服 {o['id']} ({prev['date']}), 复用; 想换加 --renew")
    elif a.pick:
        hits = [o for o in outfits if a.pick == o["id"] or a.pick in o["zh"]]
        if len(hits) != 1:
            sys.exit(f"[cover_outfit] --pick 匹配 {len(hits)} 件: {[h['id'] for h in hits]}")
        o = hits[0]
    else:
        season = season_now() if a.season == "auto" else a.season
        recent = [e["id"] for e in hist[-a.avoid_last:]] if a.avoid_last else []
        pool = [o for o in outfits if (season == "any" or season in o["tags"]) and o["id"] not in recent]
        if not pool:
            pool = [o for o in outfits if o["id"] not in recent] or outfits
        rnd = random.Random(a.seed)
        o = rnd.choice(pool)
        print(f"[cover_outfit] 季节={season} 候选={len(pool)} 避开最近={recent}")

    if a.project and not a.dry_run and not (prev and prev["id"] == o["id"] and not a.renew):
        hist.append({"date": datetime.date.today().isoformat(), "project": a.project, "id": o["id"]})
        save_history(hist)

    print(f"\n本期衣服: {o['id']} — {o['zh']}")
    print(f"参考照 (window.name 接力上传): {FACE_REF}  {'✅' if os.path.exists(FACE_REF) else '❌ 缺失, 见 docs/ONBOARDING.md 第2步'}")
    print("\nGPT prompt (一行, insertText):")
    print(PROMPT.format(outfit=o["zh"]))


if __name__ == "__main__":
    main()
