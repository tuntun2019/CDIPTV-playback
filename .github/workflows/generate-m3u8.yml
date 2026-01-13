name: Generate TV Channels M3U8

# 触发条件：定时+手动触发
on:
  schedule:
    - cron: '0 2 * * *'  # 每天 UTC 时间 2 点（北京时间 10 点）运行
  workflow_dispatch:  # 允许手动触发

# 工作流权限（允许提交代码到仓库）
permissions:
  contents: write

jobs:
  generate-m3u8:
    runs-on: ubuntu-latest
    steps:
      # 1. 拉取仓库代码
      - name: Checkout code
        uses: actions/checkout@v4
      
      # 2. 配置 Python 环境
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      # 3. 安装依赖（直接安装，跳过 requirements.txt）
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests>=2.31.0 beautifulsoup4>=4.12.2 lxml>=4.9.3
      
      # 4. 运行脚本生成 m3u8
      - name: Run m3u8 generator
        run: python main.py
      
      # 5. 提交生成的 m3u8 文件到仓库
      - name: Commit and push m3u8 file
        run: |
          git config --global user.name "GitHub Actions"
          git config --global user.email "actions@github.com"
          git add tv_channels.m3u8
          # 检查是否有变更，避免空提交
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "Auto update m3u8 file $(date +'%Y-%m-%d %H:%M:%S')"
            git push
          fi
