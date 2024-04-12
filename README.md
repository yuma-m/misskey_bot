# Misskey Bot

タイムラインの内容を学習して、マルコフ連鎖でお喋りする Misskey 用の Bot です。

## Requirements

- Python 3.12 or above
- Redis

## Usage

```bash
pip3 install -r requirements.txt
```

Misskey で以下の権限を持ったアクセストークンを発行します

- アカウントの情報を見る
- ノートを作成・削除する

```bash
SERVER_URL="wss://Misskeyのドメイン/streaming"
API_TOKEN="発行したアクセストークン"

python3 main.py
```

## カスタム辞書

`dictionary.csv` に以下の形式で記入します

```csv
単語,品詞,ヨミガナ
```
