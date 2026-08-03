name: 채용공고 자동 업데이트
on:
  schedule:
    - cron: '0 22 * * *'   # 매일 한국시간 아침 7시
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: 키 준비 (등록된 것만 사용됨)
        run: |
          if [ -n "${{ secrets.WORKNET_KEY }}" ]; then echo "${{ secrets.WORKNET_KEY }}" > worknet_key.txt; fi
          if [ -n "${{ secrets.SARAMIN_KEY }}" ]; then echo "${{ secrets.SARAMIN_KEY }}" > api_key.txt; fi
      - run: python update_jobs_all.py
      - run: rm -f worknet_key.txt api_key.txt
      - name: jobs.js 커밋 (충돌 방지)
        run: |
          git config user.name "job-bot"
          git config user.email "job-bot@users.noreply.github.com"
          git add jobs.js
          git commit -m "자동 공고 업데이트 $(date +'%Y-%m-%d %H:%M')" || { echo "변경 없음"; exit 0; }
          # 원격 최신 상태를 먼저 받아 rebase 후 push (충돌 방지)
          git pull --rebase --autostash origin main || true
          git push origin main
