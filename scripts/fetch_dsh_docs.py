# -*- coding: utf-8 -*-
"""DSH 开发文档批量下载器（VitePress → Markdown）

从 https://deepseek-harness.github.io/deepseek-harness/ 下载左侧导航全部
中文文档页，提取正文并转换为 Markdown，保存到 docs/dsh-docs/（镜像站点路径）。

用法: <venv>/bin/python scripts/fetch_dsh_docs.py
"""

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

BASE = "https://deepseek-harness.github.io/deepseek-harness"
OUT_ROOT = Path(__file__).resolve().parent.parent / "docs" / "dsh-docs"

# reference 区全部页面（2026-08-15 抓取）
REFERENCE_PAGES = [
    "/reference/agent-lifecycle",
    "/reference/capability-seams",
    "/reference/config-catalog",
    "/reference/cookbook/adding-a-conversation-node",
    "/reference/cookbook/adding-a-package",
    "/reference/cookbook/adding-a-tool",
    "/reference/cookbook/adding-an-llm-adapter",
    "/reference/cookbook/extension-cookbook",
    "/reference/cordis-api/context",
    "/reference/cordis-api/events",
    "/reference/cordis-api/fiber",
    "/reference/cordis-api/inherited",
    "/reference/cordis-api/registry",
    "/reference/cordis-api/service",
    "/reference/cordis-primer",
    "/reference/persistence-catalog",
    "/reference/subsystems/",
    "/reference/subsystems/approval",
    "/reference/subsystems/client-modules",
    "/reference/subsystems/code-runtime",
    "/reference/subsystems/commands",
    "/reference/subsystems/compaction",
    "/reference/subsystems/core",
    "/reference/subsystems/credentials",
    "/reference/subsystems/filesystem",
    "/reference/subsystems/goal",
    "/reference/subsystems/invariants",
    "/reference/subsystems/jobs",
    "/reference/subsystems/llm-streaming",
    "/reference/subsystems/lsp",
    "/reference/subsystems/permission-presets",
    "/reference/subsystems/persistence",
    "/reference/subsystems/plan",
    "/reference/subsystems/sandbox",
    "/reference/subsystems/schedule",
    "/reference/subsystems/scope",
    "/reference/subsystems/session",
    "/reference/subsystems/session-projection",
    "/reference/subsystems/session-query",
    "/reference/subsystems/session-reference",
    "/reference/subsystems/session-telemetry",
    "/reference/subsystems/session-title",
    "/reference/subsystems/settings",
    "/reference/subsystems/shell",
    "/reference/subsystems/skills",
    "/reference/subsystems/spill",
    "/reference/subsystems/storage",
    "/reference/subsystems/subagent",
    "/reference/subsystems/subprocess",
    "/reference/subsystems/system-prompt",
    "/reference/subsystems/terminal",
    "/reference/subsystems/token-meter",
    "/reference/subsystems/tools",
    "/reference/subsystems/typert",
    "/reference/subsystems/user-questions",
    "/reference/subsystems/web",
    "/reference/subsystems/web-server",
    "/reference/subsystems/workflow",
    "/reference/subsystems/workspace",
    "/reference/tool-catalog",
    "/reference/tool-execution-pipeline",
]

# 左侧导航全部文档页（2026-08-15 抓取）
PAGES = [
    "/",
    "/develop/basic/",
    "/develop/basic/config",
    "/develop/basic/publish",
    "/develop/basic/tool",
    "/develop/cordis-tutorial/",
    "/develop/cordis-tutorial/01-first-plugin",
    "/develop/cordis-tutorial/02-lifecycle-and-effects",
    "/develop/cordis-tutorial/03-services",
    "/develop/cordis-tutorial/04-events",
    "/develop/cordis-tutorial/05-config",
    "/develop/cordis-tutorial/06-composition-and-hmr",
    "/develop/cordis-tutorial/07-into-the-harness",
    "/develop/framework/",
    "/develop/framework/events",
    "/develop/framework/service",
    "/develop/practice/",
    "/develop/practice/llm-adapter",
    "/guide/quickstart",
    "/reference/",
] + REFERENCE_PAGES

# 行内转义（表格单元格中 | 需转义）
def inline_text(node) -> str:
    """递归提取行内内容（含 a/code/strong/em 标记）。"""
    if isinstance(node, NavigableString):
        return str(node)
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            name = child.name
            if name == "a":
                href = child.get("href", "")
                if href.startswith("/"):
                    href = BASE + href
                txt = inline_text(child)
                parts.append(f"[{txt}]({href})")
            elif name == "code":
                parts.append(f"`{child.get_text()}`")
            elif name in ("strong", "b"):
                parts.append(f"**{inline_text(child)}**")
            elif name in ("em", "i"):
                parts.append(f"*{inline_text(child)}*")
            elif name == "br":
                parts.append("\n")
            elif name in ("sup", "sub"):
                parts.append(child.get_text())
            elif name in ("p", "div", "span", "li", "td", "th"):
                parts.append(inline_text(child))
            else:
                parts.append(child.get_text())
    return "".join(parts)


def node_to_md(node, depth: int = 0) -> str:
    """块级元素转 Markdown。"""
    if not isinstance(node, Tag):
        return ""
    name = node.name
    out = []

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        out.append(f"\n{'#' * level} {inline_text(node)}\n")
    elif name == "p":
        txt = inline_text(node).strip()
        if txt:
            out.append(f"\n{txt}\n")
    elif name == "pre":
        code = node.get_text()
        lang = ""
        cls = node.get("class") or []
        for c in cls:
            if c.startswith("language-"):
                lang = c[len("language-"):]
        # 去掉首尾多余空行
        code = code.strip("\n")
        out.append(f"\n```{lang}\n{code}\n```\n")
    elif name in ("ul", "ol"):
        for i, li in enumerate(node.find_all("li", recursive=False)):
            marker = f"{i + 1}." if name == "ol" else "-"
            inner = " ".join(inline_text(c) for c in li.children if isinstance(c, (NavigableString, Tag)) and not (isinstance(c, Tag) and c.name in ("ul", "ol")))
            # 嵌套列表
            nested = ""
            for c in li.find_all(["ul", "ol"], recursive=False):
                nested = "\n" + "\n".join("  " + l for l in node_to_md(c).strip().splitlines())
            out.append(f"\n{marker} {inner.strip()}{nested}\n")
    elif name == "blockquote":
        text = " ".join(node_to_md(c).strip() for c in node.children if isinstance(c, Tag))
        out.append(f"\n> {text.strip()}\n")
    elif name == "table":
        rows = []
        for tr in node.find_all("tr"):
            cells = [inline_text(td).replace("|", "\\|").strip() for td in tr.find_all(["td", "th"])]
            rows.append(cells)
        if rows:
            header = rows[0]
            out.append("\n| " + " | ".join(header) + " |")
            out.append("|" + "---|" * len(header))
            for r in rows[1:]:
                out.append("| " + " | ".join(r) + " |")
            out.append("")
    elif name == "hr":
        out.append("\n---\n")
    elif name in ("div", "section", "article", "main"):
        for c in node.children:
            if isinstance(c, Tag):
                out.append(node_to_md(c, depth + 1))
    elif name in ("li",):
        out.append(node_to_md(node, depth + 1))
    return "\n".join(out)


def html_to_markdown(html: str) -> str:
    """提取 VitePress 正文并转 Markdown。"""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(class_=re.compile(r"vp-doc")) or soup.body
    if main is None:
        return ""
    return node_to_md(main)


def fetch_page(path: str) -> str:
    """下载页面 HTML。"""
    url = BASE + path if not path.startswith("http") else path
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def main() -> int:
    """批量下载并转换。"""
    total, ok, fail = len(PAGES), 0, []
    for i, path in enumerate(PAGES, 1):
        # 输出路径：/ → index.md；/develop/basic/ → develop/basic/index.md
        rel = path.strip("/")
        if rel == "":
            out = OUT_ROOT / "index.md"
        elif path.endswith("/"):
            out = OUT_ROOT / rel / "index.md"
        else:
            out = OUT_ROOT / (rel + ".md")
        print(f"[{i}/{total}] {path} -> {out.relative_to(OUT_ROOT.parent.parent)}", end="", flush=True)
        try:
            html = fetch_page(path)
            md = html_to_markdown(html)
            if not md.strip():
                # landing 首页等特殊布局：回退提取 main 文本
                soup = BeautifulSoup(html, "html.parser")
                main = soup.find("main")
                md = main.get_text("\n", strip=True) if main else ""
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md, encoding="utf-8")
            ok += 1
            print(f"  ({len(md)} 字符)")
        except Exception as exc:  # noqa: BLE001
            fail.append((path, str(exc)))
            print(f"  ✗ {exc}")
    print(f"\n完成: {ok}/{total} 成功" + (f"，失败 {len(fail)}" if fail else ""))
    for p, e in fail:
        print(f"  失败: {p} ({e})")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
