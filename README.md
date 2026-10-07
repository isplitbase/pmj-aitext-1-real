# pmj-aitext-1-real

決算書の自動分析 API (Cloud Run)。

zaiTask で PDF をアップロードしたときに動く自動分析
(サーバの `/iTaskScanPapers2` → `pys/main.py` → v2ac エンジン)を、
Cloud Run 上で **1枚単位・数枚単位でやり直せる** ようにしたもの。
画像補正ポップアップの「現在画像再分析」から使う。

```
検証(test1)   : zaiTask(.do) → pmj-door      → pmj-aitext-1      → Cloud Vision
本番(148,149) : zaiTask(.do) → pmj-door-real → pmj-aitext-1-real → Cloud Vision
```

- `pmj-aitext-1`      … 検証用
- `pmj-aitext-1-real` … 本番用

## 中身

`engine/` と `util/` は `/var/www/html/pys` からのコピー。
自動分析(決算書)の経路で使うファイルだけを持ってきている。

| ファイル | 元 | 備考 |
|---|---|---|
| `engine/v2ac.py` | pys/engine/v2ac.py | 決算書エンジン本体 |
| `engine/engine2.py` | pys/engine/engine2.py | **1か所だけ変更**(下記) |
| `engine/engine.py` | pys/engine/engine.py | |
| `engine/pre_process_image.py` | 同左 | 前処理(罫線・△・破片の除去など) |
| `engine/pre_process_imag_area.py` | 同左 | |
| `engine/v2ac_subject.csv` | 同左 | 科目の補正表 |
| `engine/hahen/` `engine/triangle/` `engine/triangle_k/` | 同左 | 前処理のテンプレート画像 |
| `util/utility.py` `util/coordinate.py` `util/defines.py` | pys/util | |
| `util/address.db` | pys/util | 住所判定 |
| `v2ac_kanjo_master.json` | pys | 勘定科目マスタ |
| `v2ac_company_master.json` | pys | 会社マスタ |
| `main.py` | **新規** | Cloud Run の入口(Flask) |

持ってきていないもの: keras の `cnn.h5`(21MB)・ginza/spacy・`getContractName.py`
(いずれも既定で OFF の機能)、PDF 用の jar、v1/v2/v2j エンジン、経営談義系、バックアップ類。

### エンジン側の変更点

`engine/engine2.py` の Vision クライアント生成の 1か所のみ(`[pmj-aitext-1]` の印)。
鍵ファイル `service-account-file.json` が無い場合は、
Cloud Run のサービスアカウントの権限(ADC)で Vision を呼ぶ。鍵ファイルは git に入れない。

また、サーバの決まったフォルダ(`/var/www/tmp/` など)へ書き出していたデバッグ用の出力
(結果の CSV・途中経過の画像 計21か所)はコメントアウトした(`[pmj-aitext-1]` の印)。
Cloud Run にはそのフォルダが無く、エラーになるため。分析結果には影響しない。

### 動作確認

test1 上で、同じ画像(itask 27731・4ページ)を
サーバの `/iTaskScanPapers2` とこのリポジトリの両方に通し、
**読み取り結果 105行が完全に一致** することを確認済み。

## エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| GET  | `/`        | ヘルスチェック(マスタの大きさ・ハッシュ) |
| POST | `/ping`    | Cloud Vision まで届くかの確認(小さな画像を1枚だけ送る) |
| POST | `/analyze` | 決算書の画像を分析する |

### POST /analyze

```json
{
  "images": ["<base64 jpeg>", "..."],
  "document_judgment_flag": "houjin",
  "resize_to": [[3311, 4680], null],
  "filenam": "12021004-20240831",
  "return_images": false
}
```

| 項目 | 必須 | 説明 |
|---|---|---|
| `images` | ○ | ページ順の画像。data URI 形式も可。PNG も可(jpg に変換して渡す) |
| `document_judgment_flag` | | `houjin`(既定) / `kojin` |
| `resize_to` | | ページごとに、このサイズへ拡大縮小してから分析。補正後画像(1024×1536 等)を元の大きさに戻すのに使う |
| `filenam` | | エンジンのログに出る名前 |
| `return_images` | | `true` でエンジンが傾き補正した画像も返す |

エンジンへの要求は、サーバのバッチ(`batch/ikisaki_itask_make.do`)の決算書経路と同じ内容で組み立てる。

返り値:

```json
{ "status": "OK", "pages": 2, "elapsed": 52.3,
  "result": { "format_info": { "cols": [ { "block_result": {
      "closing_date": { "date": "2025/09/30", "...": "..." },
      "detail": [
        { "val": "現金及び預金", "amount_this_year": "19720048", "amount_pre_year": "",
          "tabindex": 1, "page": 1, "candidate": [ ... ], "start_x": 385, "...": "..." }
      ] } } ] },
    "msg": "OK", "result": 0, "version": "..." } }
```

`detail[].tabindex` … 1=借方(総資産) / 2=貸方(総資本) / 3=損益計算書 / 4=販管費

## 必要な環境変数 (Cloud Run に設定)

すべて任意。

| 変数 | 説明 |
|---|---|
| `AITEXT_DEBUG` | `1` でエンジンのデバッグ出力をログへ出す(大量に出る) |
| `AITEXT_MAX_PAGES` | 1回に受け付ける最大ページ数。既定 20 |
| `AITEXT_MAX_MB` | 1回に受け付ける画像の合計MB。既定 30 |

鍵ファイル・API キーは不要(Cloud Run のサービスアカウントで Vision を呼ぶ)。
同じプロジェクトで Cloud Vision API が有効になっていること。

## Cloud Run の設定

| 項目 | 設定 |
|---|---|
| ビルド | **Dockerfile**(Python 3.8 固定のため。buildpacks だと版が変わる) |
| リージョン | asia-northeast1 |
| 認証 | 認証が必要 |
| メモリ / CPU | 4 GiB / 2 CPU |
| タイムアウト | 900 秒 |
| 最大同時リクエスト数 | 1(エンジンが同時に1件しか処理できないため) |

GitHub への push で自動デプロイされる。

処理時間の目安: 1ページあたり 25〜30 秒(OCR と解析)。

## ライブラリの版

サーバ(test1)の `/iTaskScanPapers2` と同じ版に固定している(`requirements.txt`)。
版を上げると OCR 結果の構造や画像処理の結果が変わり、ルールがずれるため上げないこと。

Python 3.8.5 / google-cloud-vision 0.41.0 / opencv 4.10.0.84 / numpy 1.24.4 / Pillow 9.5.0

## マスタについて

`v2ac_kanjo_master.json` / `v2ac_company_master.json` はサーバの cron
(`batch/kanri_itask_put_master.do`、毎分)が DB から作り直しているもの。
**今はリポジトリに同梱しているため、更新を反映するには push が必要。**
将来は cron で Cloud Storage へ転送し、そこから読む形にする予定。

## pmj-door 側の設定

| door | 変数 | 値 |
|---|---|---|
| `pmj-door`      | `TARGET_AITEXT1` | `pmj-aitext-1` の URL |
| `pmj-door-real` | `TARGET_AITEXT1` | `pmj-aitext-1-real` の URL |

あわせて、door のサービスアカウントにこのサービスへの `roles/run.invoker` を付与する。

呼び出し方:

```json
POST /call
{ "target": "aitext1", "path": "/analyze",
  "payload": { "images": ["..."], "document_judgment_flag": "houjin" } }
```
