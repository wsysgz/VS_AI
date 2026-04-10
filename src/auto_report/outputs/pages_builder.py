"""GitHub Pages 站点构建器 — 将 HTML 报告部署为在线快报站"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from auto_report.outputs.renderers import render_html_report


def _read_archives(archives_dir: Path) -> list[dict[str, str]]:
    """读取历史归档 HTML 文件，按日期倒序排列（递归搜索日期子目录）"""
    entries: list[dict[str, str]] = []
    if not archives_dir.exists():
        return entries

    # 归档文件在 YYYY-MM-DD/ 子目录中
    for f in sorted(archives_dir.rglob("*.html"), reverse=True):
        stem = f.stem
        # 从文件名提取日期 (格式: 2026-04-11T00-38-18...summary)
        date_str = stem.replace("summary-", "").split("T")[0]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            display = dt.strftime("%Y年%m月%d日")
        except ValueError:
            display = stem

        # 去重：同一天只保留最新的一个
        if date_str and any(e["date"] == date_str for e in entries):
            continue

        entries.append({
            "filename": f.name,
            "date": date_str,
            "display": display,
            "url": f"archives/{f.parent.name}/{f.name}",
        })

    return entries


def _build_site_index(
    latest_html: str,
    archives: list[dict[str, str]],
    generated_at: str,
) -> str:
    """构建带导航的站点首页 (index.html)"""
    nav_items = ""
    for entry in archives[:14]:  # 最近2周
        active = ' class="nav-active"' if entry == archives[0] else ""
        nav_items += f'<li{active}><a href="{entry["url"]}">{entry["display"]}</a></li>\n'

    archive_links = "\n".join(
        f'<a class="archive-pill" href="{a["url"]}">{a["display"]}</a>'
        for a in archives[:14]
    ) or '<span class="text-muted">暂无历史报告</span>'

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VS_AI 情报快报站</title>
<style>
  :root {{
    --bg:#0d1117; --bg2:#161b22; --bg3:#1c2333; --border:#30363d;
    --text:#e6edf3; --text2:#8b949e; --accent:#58a6ff; --green:#3fb950;
    --orange:#d29922; --red:#f85149; --purple:#bc8cff; --radius:10px;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg:#ffffff;--bg2:#f6f8fa;--bg3:#eaeef2;--border:#d0d7de;
      --text:#1f2328;--text2:#656d76;--accent:#0969da;--green:#1a7f37;
      --orange:#9a6700;--red:#cf222e;--purple:#8250df;
    }}
  }}
  * {{ box-sizing:border-box;margin:0;padding:0; }}
  body {{ background:var(--bg);color:var(--text);line-height:1.6;transition:background .3s,color .3s; }}
  .site-wrap {{ max-width:1100px;margin:0 auto;padding:0 20px 48px; }}

  /* ── Top Navigation ── */
  .top-nav {{
    position:sticky;top:0;z-index:100;background:var(--bg);
    border-bottom:1px solid var(--border);padding:10px 0;margin-bottom:24px;
    backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  }}
  .top-nav-inner {{ max-width:1100px;margin:0 auto;padding:0 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap; }}
  .site-logo {{ font-size:1.15em;font-weight:700;color:var(--accent);text-decoration:none;white-space:nowrap; }}
  .site-logo span {{ background:linear-gradient(135deg,var(--accent),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent; }}
  .nav-tagline {{ color:var(--text2);font-size:.8em; }}
  .nav-time {{ margin-left:auto;color:var(--text2);font-size:.78em;white-space:nowrap; }}

  /* ── Hero / Latest Report ── */
  .hero-section {{ margin-bottom:36px; }}
  .hero-meta {{ display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px; }}
  .badge-live {{ background:rgba(63,185,80,.15);color:var(--green);font-size:.78em;font-weight:600;padding:3px 12px;border-radius:12px;border:1px solid rgba(63,185,80,.3); }}

  /* ── Archive Navigator ── */
  .archive-section {{ margin-bottom:32px; }}
  .archive-header {{ display:flex;align-items:center;justify-content:space-between;margin-bottom:14px; }}
  .archive-header h2 {{ font-size:1.08em;color:var(--text2);font-weight:600; }}
  .archive-grid {{ display:flex;flex-wrap:wrap;gap:8px; }}
  .archive-pill {{
    padding:5px 14px;border-radius:16px;font-size:.82em;text-decoration:none;
    color:var(--text2);background:var(--bg3);border:1px solid var(--border);
    transition:all .2s;white-space:nowrap;
  }}
  .archive-pill:hover {{ border-color:var(--accent);color:var(--accent);transform:translateY(-1px); }}

  /* ── Footer ── */
  footer {{ text-align:center;padding:28px 0 8px;border-top:1px solid var(--border);margin-top:40px;color:var(--text2);font-size:.82em; }}
  footer a {{ color:var(--accent);text-decoration:none; }}
  footer a:hover {{ text-decoration:underline; }}

  /* ── Responsive ── */
  @media(max-width:640px) {{
    .top-nav-inner {{ flex-direction:column;align-items:flex-start;gap:6px; }}
    .nav-time {{ margin-left:0; }}
    .site-logo {{ font-size:1em; }}
    .archive-grid {{ gap:6px; }}
    .archive-pill {{ font-size:.76em;padding:4px 10px; }}
  }}
</style>
</head>
<body>
<nav class="top-nav">
  <div class="top-nav-inner">
    <a class="site-logo" href="/"><span>🔭 VS_AI 情报快报</span></a>
    <span class="nav-tagline">AI/电子产业每日情报 · 自动采集分析</span>
    <span class="nav-time">更新于 {generated_at}</span>
  </div>
</nav>

<div class="site-wrap">

  <!-- 最新报告直接嵌入 -->
  <section class="hero-section">
    <div class="hero-meta">
      <span class="badge-live">● 最新报告</span>
      <span style="color:var(--text2);font-size:.85em;">{generated_at}</span>
    </div>
    {latest_html}
  </section>

  <!-- 历史导航 -->
  <section class="archive-section">
    <div class="archive-header">
      <h2>📚 历史报告 ({len(archives)} 期)</h2>
    </div>
    <div class="archive-grid">
      {archive_links}
    </div>
  </section>

  <footer>
    <p><a href="https://github.com/wsysgz/VS_AI" target="_blank" rel="noopener">VS_AI</a> 情报采集系统自动生成</p>
    <p style="margin-top:4px;">数据来源：RSS / GitHub / 官方网站 &middot; AI 驱动分析</p>
  </footer>

</div>
</body>
</html>'''


def build_pages_site(root_dir: Path) -> Path:
    """
    构建完整的 GitHub Pages 站点到 root_dir/docs/
    
    部署方式：GitHub Pages 从 main 分支的 docs/ 目录读取（无需 gh-pages 分支）
    
    输出结构：
    docs/
    ├── index.html          (首页 + 最新报告嵌入)
    └── archives/
        ├── 2026-04-11/
        └── 2026-04-10/
    """
    reports_dir = root_dir / "data" / "reports"
    archives_dir = root_dir / "data" / "archives"
    dist_dir = root_dir / "docs"
    archives_dist = dist_dir / "archives"

    # 清理旧的构建输出
    if dist_dir.exists():
        # 只清理生成的文件，保留 docs 目录本身可能存在的其他文件（如 .nojekyll）
        for item in dist_dir.iterdir():
            if item.name != ".nojekyll":
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    archives_dist.mkdir(parents=True, exist_ok=True)

    # 确保 .nojekyll 存在（让 GitHub Pages 正确处理 _ 开头的目录/文件）
    nojekyll = dist_dir / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.touch()

    # 读取最新报告
    latest_html_path = reports_dir / "latest-summary.html"
    if not latest_html_path.exists():
        raise FileNotFoundError(f"Latest report not found: {latest_html_path}")

    latest_html_content = latest_html_path.read_text(encoding="utf-8")

    # 提取报告标题和时间（从 HTML 内容中）
    generated_at = "未知时间"
    for pattern in ["生成时间：(.*?)<", "generated_at.*?>(.*?)<"]:
        import re
        m = re.search(pattern, latest_html_content)
        if m:
            generated_at = m.group(1).strip()
            break

    # 读取历史归档
    archives = _read_archives(archives_dir)

    # 复制历史归档到站点目录（保留日期子目录结构）
    for entry in archives:
        src = archives_dir / entry["url"].replace("archives/", "")
        if src.exists():
            dest = archives_dist / entry["url"].replace("archives/", "")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    # 同时复制最新报告到归档（以当前日期命名）
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = archives_dist / today
    today_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest_html_path, today_dir / f"latest-summary-{datetime.now().strftime('%H-%M-%S')}.html")

    # 构建首页
    index_html = _build_site_index(latest_html_content, archives, generated_at)

    with open(dist_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"[Pages] Site built at {dist_dir}")
    print(f"[Pages] Index: {dist_dir / 'index.html'}")
    print(f"[Pages] Archives: {len(list(archives_dist.glob('*.html')))} files")
    
    return dist_dir
