"""render_video.py — 批次把 render_manifest.json 的鏡頭送去 Kling / Seedance 生成。

⚠️ 誠實說明：實際生成需要你自己的 Kling / Seedance 帳號金鑰與 API 端點。
   本沙箱環境沒有金鑰、也無法連外，因此預設以 --dry-run 執行：
   只驗證 manifest、組出每個 job 的請求 payload、印出計畫，不呼叫任何外部服務。
   等你在自己的機器設好環境變數，拿掉 --dry-run 就會真的送出。

環境變數（真跑時）：
  VIDEO_API_KEY       你的 Kling / Seedance 金鑰
  VIDEO_ENDPOINT      生成 API 的 URL（依 provider 文件）
  VIDEO_POLL_ENDPOINT （選填）查詢任務狀態的 URL 模板，含 {task_id}

用法：
  python render_video.py <manifest.json> <輸出資料夾> [--dry-run] [--limit N]

注意：不同 provider 的 request/response 欄位不同。下方 build_payload() 是
      通用範本，請對照你 provider 當前 API 文件微調欄位名稱。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def build_payload(job: dict) -> dict:
    """通用文生影片請求範本。依你的 provider API 調整欄位名。"""
    return {
        "prompt": job["prompt"],
        "duration": job["duration_sec"],
        "aspect_ratio": job["aspect"],
        "negative_prompt": "horror, superstition, exaggeration, supernatural, text watermark",
        "cfg_scale": 0.5,
        "mode": "std",
    }


def submit(endpoint: str, key: str, payload: dict) -> dict:
    """真跑時才會被呼叫。用標準庫 urllib，不加依賴。"""
    import urllib.request
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("outdir")
    ap.add_argument("--dry-run", action="store_true", help="只驗證與印計畫，不呼叫 API")
    ap.add_argument("--limit", type=int, default=0, help="只處理前 N 個 job（試跑用）")
    a = ap.parse_args()

    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    jobs = manifest["jobs"]
    if a.limit:
        jobs = jobs[:a.limit]

    key = os.environ.get("VIDEO_API_KEY", "")
    endpoint = os.environ.get("VIDEO_ENDPOINT", "")
    dry = a.dry_run or not (key and endpoint)

    outdir = Path(a.outdir)
    (outdir / "payloads").mkdir(parents=True, exist_ok=True)

    print(f"=== render_video ===  provider={manifest['tool']}  jobs={len(jobs)}  "
          f"{'DRY-RUN（未實際生成）' if dry else 'LIVE'}")
    if dry and not (key and endpoint):
        print("ℹ️  未偵測到 VIDEO_API_KEY / VIDEO_ENDPOINT → 自動切 dry-run。")

    total_sec = 0.0
    for job in jobs:
        if not job["prompt"]:
            print(f"  shot {job['shot']}: ⚠️ 無 prompt，略過")
            continue
        payload = build_payload(job)
        total_sec += job["duration_sec"]
        (outdir / "payloads" / f"{job['output']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if dry:
            print(f"  shot {job['shot']}: {job['duration_sec']:.0f}s → {job['output']} "
                  f"(payload {len(json.dumps(payload))}B)")
        else:
            try:
                resp = submit(endpoint, key, payload)
                print(f"  shot {job['shot']}: 已送出 task={resp.get('task_id', resp)}")
                # 真跑：這裡接 poll + 下載 mp4 到 outdir（依 provider response 實作）
            except Exception as e:  # noqa: BLE001
                print(f"  shot {job['shot']}: ❌ {type(e).__name__}: {e}")

    print(f"\n合計影片長度 ≈ {total_sec:.0f}s。payload 已寫到 {outdir/'payloads'}。")
    if dry:
        print("下一步：在自有環境設 VIDEO_API_KEY / VIDEO_ENDPOINT，拿掉 --dry-run 即真生成。")


if __name__ == "__main__":
    main()
