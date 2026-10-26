#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csmusic 无头自检：曲目清单解析 + 下载文件名安全化。

``download_mp3.py`` 是脚本式模块：import 期就读取 ``_all_music_urls.txt``、建专辑
目录，并直接把线程池下载跑起来。为了在不联网、不落盘、不改项目的前提下验证它
真正的解析逻辑，自检在 import 前注入三个替身：

* ``requests``  -> ``get()`` 直接报错（保证一个网络请求都不会发出）；
* ``concurrent.futures.ThreadPoolExecutor`` / ``as_completed`` -> 空执行器 / 空迭代；
* ``os.makedirs`` -> 空操作（import 期的建目录不落盘）。

替身只在 import 期间生效，随后立即恢复。验证点：
1. 清单解析：多行专辑头 ``[无拘空间 / Floorspace]`` 合并、tab 分隔行、扩展名推导；
   任务数/专辑数达到数据规模，且 (专辑, 文件名) 无重复。
2. 文件名安全化：非法字符替换、首尾空白裁剪、换行转下划线。
"""
from __future__ import annotations

import concurrent.futures as _cf
import contextlib
import io
import os
import sys
import types
from pathlib import Path

sys.dont_write_bytecode = True          # 不在项目里留 .pyc
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

EXTS = (".mp3", ".wav", ".ogg")
ILLEGAL = '\\/:*?"<>|'


class CheckError(RuntimeError):
    pass


def check(condition, message):
    if not condition:
        raise CheckError(message)


def import_downloader():
    """在替身环境里 import download_mp3：只执行清单解析，不联网/不落盘。"""
    fake_requests = types.ModuleType("requests")

    def _blocked(*_args, **_kwargs):
        raise CheckError("download_mp3 tried to issue a network request during selfcheck")

    fake_requests.get = _blocked
    previous_requests = sys.modules.get("requests")
    sys.modules["requests"] = fake_requests

    class _NoopExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def submit(self, *args, **kwargs):
            return None

    real_executor = _cf.ThreadPoolExecutor
    real_as_completed = _cf.as_completed
    real_makedirs = os.makedirs
    _cf.ThreadPoolExecutor = _NoopExecutor
    _cf.as_completed = lambda futures: iter(())
    os.makedirs = lambda *args, **kwargs: None
    try:
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            import download_mp3
        return download_mp3, captured.getvalue()
    finally:
        os.makedirs = real_makedirs
        _cf.ThreadPoolExecutor = real_executor
        _cf.as_completed = real_as_completed
        if previous_requests is None:
            sys.modules.pop("requests", None)
        else:
            sys.modules["requests"] = previous_requests


def check_manifest(downloader, import_log):
    tasks = downloader.tasks
    check(len(tasks) > 1000, f"解析出的下载任务过少：{len(tasks)}")
    albums = {task[0] for task in tasks}
    check(len(albums) >= 90, f"解析出的专辑过少：{len(albums)}")

    pairs = [(task[0], task[1]) for task in tasks]
    check(len(set(pairs)) == len(pairs), "存在重复的 (专辑, 文件名) 任务")

    # 多行专辑头 "[无拘空间\nFloorspace]" 应合并为下划线命名；首曲来自该专辑。
    first_album, first_track, first_url = tasks[0]
    check(first_album == "无拘空间_Floorspace",
          f"多行专辑头解析错误：{first_album!r}")
    check(first_track == "主菜单.mp3", f"首曲文件名解析错误：{first_track!r}")
    check(first_url.endswith("main_menu.mp3"), f"首曲 URL 解析错误：{first_url!r}")

    for album, track, url in tasks:
        check(isinstance(album, str) and album, f"专辑名为空：{album!r}")
        check(isinstance(track, str) and track, f"文件名为空：{track!r}")
        check(url.startswith(("http://", "https://")), f"URL 非 http(s)：{url!r}")
        extension = next((ext for ext in EXTS if track.lower().endswith(ext)), None)
        check(extension is not None, f"文件名缺少音频扩展名：{track!r}")
        check(extension in url.lower(), f"扩展名与 URL 不符：{track!r} <- {url!r}")
        check(not any(ch in track for ch in ILLEGAL),
              f"文件名仍含路径/保留字符：{track!r}")

    check("下载任务" in import_log, "import 期没有输出解析计数日志")
    return len(tasks), len(albums)


def check_sanitize(downloader):
    sanitize = downloader.sanitize
    check(sanitize('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j",
          "sanitize 未把 Windows 非法字符统一替换为下划线")
    check(sanitize("  name\nx ") == "name_x",
          "sanitize 未裁剪首尾空白/未把换行转为下划线")
    check(sanitize("主菜单") == "主菜单", "sanitize 误改了合法中文名")


def main():
    downloader, import_log = import_downloader()
    task_count, album_count = check_manifest(downloader, import_log)
    check_sanitize(downloader)
    print(
        "selfcheck ok: parsed %d download tasks / %d albums from _all_music_urls.txt "
        "(multi-line album headers, ext inference, no duplicate pairs) + filename sanitize"
        % (task_count, album_count)
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - 自检入口需要把任何失败转成 FAIL + 退出码 1
        print(f"FAIL: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
