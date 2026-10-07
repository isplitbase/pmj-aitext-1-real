# -*- coding: utf-8 -*-
"""pmj-aitext-1 : 決算書の自動分析 API (Cloud Run)

  zaiTask で PDF をアップロードしたときに動く自動分析
  (サーバの /iTaskScanPapers2 → pys/main.py → v2ac エンジン)を、
  Cloud Run で 1枚単位・数枚単位でやり直せるようにしたもの。

      zaiTask(.do) → pmj-door(-real) → [このサービス] → Cloud Vision

  engine/ と util/ は /var/www/html/pys からのコピー。
  自動分析(決算書)の経路で使うファイルだけを持ってきている。
  エンジン側の変更は engine2.py の Vision 認証 1か所のみ([pmj-aitext-1] の印)。

  エンドポイント:
    GET  /         … ヘルスチェック(マスタの大きさ・ハッシュ)
    POST /ping     … Cloud Vision まで届くかの確認(小さな画像を1枚だけ送る)
    POST /analyze  … 決算書の画像を分析する

  POST /analyze の入力:
    {
      "images": ["<base64 jpeg>", ...],       # 必須。ページ順。data URI 形式も可
      "document_judgment_flag": "houjin",    # 任意。houjin / kojin (既定 houjin)
      "resize_to": [[3311, 4680], null, ...], # 任意。ページごとに、このサイズへ拡大縮小してから分析
      "filenam": "…",                        # 任意。エンジンのログに出る名前
      "return_images": false                 # 任意。エンジンが傾き補正した画像も返す
    }
  返り値:
    { "status": "OK", "result": <エンジンの返り値そのまま>, "elapsed": 12.3,
      "pages": 2, "images": [...] (return_images 指定時のみ) }

  result の中身はサーバの自動分析と同じ形。
    result.format_info.cols[0].block_result.detail[] に 1行ずつ
      val(読み取った科目名) / candidate(マスタ候補) /
      amount_this_year / amount_pre_year / tabindex(1借方 2貸方 3損益 4販管費) / page / 座標
    が入る。

  環境変数 (Cloud Run に設定):
    AITEXT_DEBUG      … 任意。1 にするとエンジンのデバッグ出力をログへ出す(大量に出る)
    AITEXT_MAX_PAGES  … 任意。1回に受け付ける最大ページ数。既定 20
    AITEXT_MAX_MB     … 任意。1回に受け付ける画像の合計MB。既定 30
"""

import base64
import binascii
import contextlib
import datetime
import glob
import hashlib
import io
import os
import shutil
import tempfile
import threading
import time
import traceback

import cv2
import numpy as np
from flask import Flask, jsonify, request

import util.defines  # noqa: F401  (エンジンが前提にしている読み込み順を守る)
import util.utility
from util.utility import init_address_data

# エンジンが返す version 文字列に入る。pys/main.py と同じ値にしておく
MAIN_VERSION_STR = "1.0.031.vx"

# 住所データの初期化(pys/main.py と同じく起動時に1回)
init_address_data()

from engine.v2ac import v2ac  # noqa: E402

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_PAGES = int(os.environ.get("AITEXT_MAX_PAGES", "20"))
MAX_BYTES = int(float(os.environ.get("AITEXT_MAX_MB", "30")) * 1024 * 1024)
DEBUG = os.environ.get("AITEXT_DEBUG", "0") == "1"

# エンジンはモジュール変数(デバッグ出力先・初期化済みフラグ等)を持っていて
# 同時に2件流すと混ざるため、1件ずつ順番に処理する
_LOCK = threading.Lock()

# エンジンのデバッグ出力(既定は大量に出る設定)を、普段は捨てる
if not DEBUG:
    util.utility.debug_file = open(os.devnull, "w", encoding="utf-8")


def _decode_image(value):
    """base64(または data URI)を生バイトに戻す。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("画像が空です")
    s = value.strip()
    if s.startswith("data:"):
        s = s.partition(",")[2]
    s = "".join(s.split())
    try:
        raw = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("base64 を復号できません")
    if not raw:
        raise ValueError("画像が空です")
    return raw


def _write_page(raw, path, resize_to):
    """1ページ分を jpg で書き出す。必要なら指定サイズへ拡大縮小する。"""
    is_jpeg = raw[:3] == b"\xff\xd8\xff"
    if is_jpeg and not resize_to:
        # 何も手を加えない場合は、受け取ったバイト列をそのまま置く(再圧縮しない)
        with open(path, "wb") as f:
            f.write(raw)
        return
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("画像として読めません")
    if resize_to:
        w, h = int(resize_to[0]), int(resize_to[1])
        if w <= 0 or h <= 0:
            raise ValueError("resize_to が不正です")
        if (w, h) != (img.shape[1], img.shape[0]):
            enlarge = w * h > img.shape[0] * img.shape[1]
            img = cv2.resize(img, (w, h),
                             interpolation=cv2.INTER_CUBIC if enlarge else cv2.INTER_AREA)
    ok = cv2.imwrite(path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not ok:
        raise ValueError("画像を書き出せませんでした")


def _make_request(root_str, n, flag, filenam):
    """サーバのバッチ(ikisaki_itask_make.do)の決算書経路と同じ要求を作る。"""
    return {
        "type": "v2ac",
        "analyze": "analysis_by_format",
        "filenam": filenam,
        "document_judgment_flag": flag,
        "root_str": root_str,
        "extension": ".jpg",
        "number_of_images": n,
        "calibration": None,
        "height_adjust": 0.9,
        "format_info": {
            "format_id": "",
            "cols": [{"col_conditions": [{"conditions_id": "100"}]}],
        },
    }


def _run_engine(json_data, capture=None):
    """pys/main.py の application() と同じ手順でエンジンを動かす。

    capture に io.StringIO を渡すと、エンジンのデバッグ出力をそこへ集める(調査用)。
    """
    response = {"result": 0}
    saved_debug_file = util.utility.debug_file
    if capture is not None:
        util.utility.debug_file = capture
        sink = contextlib.redirect_stdout(capture)
    elif DEBUG:
        sink = contextlib.nullcontext()
    else:
        # エンジンは print() でも大量に出力するので、普段は捨てる(エラーはログに残す)
        sink = contextlib.redirect_stdout(util.utility.debug_file)
    try:
        with sink:
            pdata = v2ac(json_data, datetime.datetime.now(),
                         main_version=MAIN_VERSION_STR, debug_suffix="")
            pdata.init_AI()
            pdata.OpenPapers()
            response = pdata.getResultJson()
        response["msg"] = "OK"
        response["result"] = 0
    except KeyError:
        response["msg"] = "Parameter Error>\n" + traceback.format_exc()
        response["result"] = -100
        traceback.print_exc()
    except Exception:
        response["msg"] = "Error>\n" + traceback.format_exc()
        response["result"] = -200
        traceback.print_exc()
    finally:
        util.utility.debug_file = saved_debug_file
    return response


# 調査用: どの版が動いているか・実行環境の情報
API_VERSION = "2026-10-07-debug1"


def _env_info():
    import locale
    import platform
    import sys
    try:
        import google.cloud.vision as _v
        vision_file = _v.__file__
    except Exception:
        vision_file = None
    return {
        "api_version": API_VERSION,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "lang": os.environ.get("LANG"),
        "preferred_encoding": locale.getpreferredencoding(False),
        "fs_encoding": sys.getfilesystemencoding(),
        "cv2": cv2.__version__,
        "numpy": np.__version__,
        "vision_file": vision_file,
        "cwd": os.getcwd(),
    }


_MASTER_INFO = None


def _master_info():
    """マスタの大きさと短いハッシュ(どの版が入っているかの確認用)。"""
    global _MASTER_INFO
    if _MASTER_INFO is None:
        info = {}
        for name in ("v2ac_kanjo_master.json", "v2ac_company_master.json"):
            p = os.path.join(BASE_DIR, name)
            if os.path.exists(p):
                with open(p, "rb") as f:
                    info[name] = {"bytes": os.path.getsize(p),
                                  "md5": hashlib.md5(f.read()).hexdigest()[:12]}
            else:
                info[name] = None
        _MASTER_INFO = info
    return _MASTER_INFO


@app.get("/")
def health():
    return jsonify({
        "status": "ok",
        "service": os.environ.get("K_SERVICE", "pmj-aitext-1"),  # Cloud Run が自動で設定
        "engine": "v2ac",
        "main_version": MAIN_VERSION_STR,
        "masters": _master_info(),
    })


@app.post("/ping")
def ping():
    """Cloud Vision まで届くか(権限があるか)の確認。小さな画像を1枚だけ送る。"""
    try:
        from google.cloud import vision
        from google.cloud.vision import types
        img = np.full((60, 200, 3), 255, np.uint8)
        cv2.putText(img, "12345", (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
        ok, buf = cv2.imencode(".png", img)
        client = vision.ImageAnnotatorClient()
        res = client.text_detection(image=types.Image(content=buf.tobytes()))
        if res.error.message:
            return jsonify({"status": "NG", "error": res.error.message}), 502
        text = res.text_annotations[0].description.strip() if res.text_annotations else ""
    except Exception as e:
        return jsonify({"status": "NG", "error": str(e)[:500]}), 502
    return jsonify({"status": "OK", "text": text, "env": _env_info()})


@app.post("/analyze")
def analyze():
    body = request.get_json(silent=True) or {}

    images = body.get("images")
    if not isinstance(images, list) or not images:
        return jsonify({"status": "NG", "error": "images が空です"}), 400
    if len(images) > MAX_PAGES:
        return jsonify({"status": "NG",
                        "error": "ページが多すぎます(最大 %d)" % MAX_PAGES}), 400

    flag = str(body.get("document_judgment_flag") or "houjin")
    if flag not in ("houjin", "kojin"):
        return jsonify({"status": "NG",
                        "error": "document_judgment_flag は houjin / kojin のいずれかです"}), 400

    resize_list = body.get("resize_to") or []
    if not isinstance(resize_list, list):
        return jsonify({"status": "NG", "error": "resize_to は配列で指定してください"}), 400

    filenam = str(body.get("filenam") or "aitext")
    want_images = bool(body.get("return_images"))

    # 画像を復号(合計サイズも確認)
    raws = []
    total = 0
    try:
        for i, v in enumerate(images):
            raw = _decode_image(v)
            total += len(raw)
            raws.append(raw)
    except ValueError as e:
        return jsonify({"status": "NG", "error": "%d枚目: %s" % (len(raws) + 1, e)}), 400
    if total > MAX_BYTES:
        return jsonify({"status": "NG",
                        "error": "画像が大きすぎます(合計 %.1f MB)" % (total / 1048576.0)}), 400

    t0 = time.time()
    work = tempfile.mkdtemp(prefix="aitext_")
    try:
        # エンジンは root_str + 番号 + 拡張子 のファイルを読むので、同じ形で置く
        root_str = os.path.join(work, "content_")
        for i, raw in enumerate(raws):
            resize_to = resize_list[i] if i < len(resize_list) else None
            try:
                _write_page(raw, root_str + str(i) + ".jpg", resize_to)
            except ValueError as e:
                return jsonify({"status": "NG", "error": "%d枚目: %s" % (i + 1, e)}), 400

        json_data = _make_request(root_str, len(raws), flag, filenam)
        capture = io.StringIO() if body.get("debug") else None
        with _LOCK:
            result = _run_engine(json_data, capture)

        out = {
            "status": "OK" if result.get("result") == 0 else "NG",
            "result": result,
            "pages": len(raws),
            "elapsed": round(time.time() - t0, 1),
        }
        if out["status"] != "OK":
            out["error"] = (result.get("msg") or "")[:1000]

        if capture is not None:
            # 調査用: エンジンのデバッグ出力(長いので先頭と末尾だけ)と実行環境
            log = capture.getvalue()
            out["debug_log_head"] = log[:60000]
            out["debug_log_tail"] = log[-60000:]
            out["debug_log_bytes"] = len(log)
            out["env"] = _env_info()

        if want_images:
            # エンジンが傾き補正した画像(サーバでは /data/iimgs に入るもの)
            tilt = []
            for i in range(len(raws)):
                files = sorted(glob.glob(root_str + "*" + str(i) + ".jpg.tilt.jpg"))
                if files:
                    with open(files[0], "rb") as f:
                        tilt.append(base64.b64encode(f.read()).decode("ascii"))
                else:
                    tilt.append(None)
            out["images"] = tilt

        return jsonify(out), (200 if out["status"] == "OK" else 500)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
