> ⚠️ **已不再维护 / Archived — No longer maintained**
>
> 本仓库已停止开发投入，仅作归档保留，不再接收功能更新或 issue。代码保持原样，仅供历史参考。
> _This repository is no longer maintained. It is archived as-is for historical reference only._

# csmusic

Counter-Strike（CS:GO/CS2）音乐盒（Music Kit）MP3 成品库，含一个批量下载脚本。

## 类型
数据目录（音乐盒曲目库，含下载脚本）

## 目录要点
- 94 个「音乐盒」子目录：已下载的 CS 音乐盒曲目（如 8位音乐盒、CSGO精彩时刻、EZ4ENCE 等）
  —— **本地保留，不入库**（1138 个 MP3）
- download_mp3.py：从 _all_music_urls.txt 批量下载 MP3（多线程、专辑头解析）
- _all_music_urls.txt：待下载曲目 URL 清单（**已入库**，据此可复现全部曲目）
- music kit.txt：音乐盒说明

## 用途
存放 CS 音乐盒成品 MP3，供采样、混音、电台等下游管线使用。

## 仓库说明
- 本仓只入库**脚本 + 曲目清单 + 说明**；MP3 成品（676 MB）属资源池，由 `.gitignore` 排除。
- 2026-10-26 由 `G:\assets\csmusic` 迁入 `G:\repos\csmusic`（合并同类项：G:\assets 整体是资源池，
  其中带脚本的项按 fonts / radio_special_instruments 的路子建仓归位）。
  同期修掉 `download_mp3.py` 里写死的旧址 `G:\music\csmusic`，改为**脚本自身所在目录**。

## 测试状态
download_mp3.py 通过 py_compile 语法检查（syntax_ok）。
