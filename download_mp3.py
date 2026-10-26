import os, re, time, requests, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# 2026-10-26 迁入 G:\repos\csmusic 后改为「脚本自身所在目录」，不再写死绝对路径
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT_DIR, exist_ok=True)

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip().replace("\n", "_")

def log(m):
    try:
        print(m, flush=True)
    except Exception:
        pass

# 解析 _all_music_urls.txt
url_file = os.path.join(OUT_DIR, "_all_music_urls.txt")
tasks = []

with open(url_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

album_lines = []  # 收集多行的专辑头
in_album = False
for line in lines:
    line_orig = line
    line = line.strip()
    if line.startswith("[") and not line.endswith("]"):
        # 多行专辑头开始
        album_lines = [line[1:]]
        in_album = True
        continue
    if in_album:
        if line.endswith("]"):
            album_lines.append(line[:-1])
            current_album = sanitize("_".join(album_lines))
            in_album = False
        else:
            album_lines.append(line)
        continue
    # 非专辑头 → 歌曲行
    if "\thttp" in line:
        parts = line.split("\t", 1)
        track_name = sanitize(parts[0])
        url = parts[1].strip()
        ext = ".mp3"
        for e in [".mp3", ".wav", ".ogg"]:
            if e in url.lower():
                ext = e
                break
        if not track_name.lower().endswith(ext):
            track_name += ext
        tasks.append((current_album, track_name, url))
    elif line.startswith("http"):
        m = re.match(r'^(.*?)\s+(https?://.+)$', line)
        if m:
            track_name = sanitize(m.group(1))
            url = m.group(2).strip()
            ext = ".mp3"
            for e in [".mp3", ".wav", ".ogg"]:
                if e in url.lower():
                    ext = e
                    break
            if not track_name.lower().endswith(ext):
                track_name += ext
            tasks.append((current_album, track_name, url))

log(f"解析到 {len(tasks)} 个下载任务")

# 建立目录
for album, _, _ in tasks:
    os.makedirs(os.path.join(OUT_DIR, album), exist_ok=True)

def download(task):
    album, track_name, url = task
    path = os.path.join(OUT_DIR, album, track_name)
    # 如果"未知专辑"里已有文件，先移动过来
    old_path = os.path.join(OUT_DIR, "未知专辑", track_name)
    if os.path.exists(old_path) and os.path.getsize(old_path) > 100:
        if not os.path.exists(path):
            shutil.move(old_path, path)
        return f"[复用] {album}/{track_name}"
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return f"[跳过] {album}/{track_name}"
    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.csgo.com.cn/data/music_box.html"
        }, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 100:
            with open(path, "wb") as f:
                f.write(resp.content)
            return f"[OK] {album}/{track_name} ({len(resp.content)} bytes)"
        else:
            return f"[FAIL {resp.status_code}] {album}/{track_name}"
    except Exception as e:
        return f"[ERR] {album}/{track_name}: {e}"

start = time.time()
done, failed, reused = 0, 0, 0
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(download, t): t for t in tasks}
    for fut in as_completed(futures):
        msg = fut.result()
        done += 1
        if "[OK]" in msg:
            pass
        elif "[复用]" in msg:
            reused += 1
        elif "[跳过]" in msg:
            reused += 1
        else:
            failed += 1
        if done % 50 == 0:
            elapsed = time.time() - start
            log(f"进度: {done}/{len(tasks)} ({done*100//len(tasks)}%) | 失败:{failed} | {elapsed:.0f}s")

elapsed = time.time() - start
log(f"\n完成! 共 {len(tasks)} 首, 复用 {reused}, 失败 {failed}, 总耗时 {elapsed:.0f}s")
log(f"文件保存在: {OUT_DIR}")
