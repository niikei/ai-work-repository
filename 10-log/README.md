# Log

会議、作業、障害、判断など「何が起きたか」を日付順に記録します。

Logは月ではなく、月曜日の開始日を表す週ディレクトリへ保存します。

```text
10-log/YYYY/MM/YYYY-MM-DD-week/YYYY-MM-DD-slug.md
```

たとえば2026年7月29日のLogは、次の場所になります。

```text
10-log/2026/07/2026-07-27-week/2026-07-29-upgrade-meeting.md
```

年直下は12か月、月直下は通常4〜5週だけになるため、ファイルツリーを見渡しやすくなります。
月は出来事の日付ではなく週の開始日で決まるため、月をまたいでも同じ業務週の出来事は
分断されません。週の計算と保存先は`workrepo new log`が自動的に決定します。

Logは履歴と根拠であり、ProjectやAreaの現在状態そのものではありません。重要な変化は
関連する`index.md`にも反映します。

電話・メール・短い作業が多い日は、出来事ごとにファイルを増やさず、日次Logへまとめられます。

```shell
uv run workrepo new log daily --title "2026-07-29 Daily Log" --template daily
```

未整理の思いつきはInbox、後から参照する一回の出来事はLog、継続的に追う次の行動は
ProjectまたはAreaへ置くのが基準です。
