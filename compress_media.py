import os
import shutil
import subprocess
import re

website_dir = r"E:\WIKI_LLM\website"
index_path = os.path.join(website_dir, "index.html")
web_media_dir = os.path.join(website_dir, "media_web")

with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

# Find all src: "media/..." or thumbSrc: "media/..."
matches = sorted(set(re.findall(r'media/[^"\']+', html)))

print(f"Found {len(matches)} media references in index.html")

ffmpeg_exe = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
if not os.path.exists(ffmpeg_exe):
    ffmpeg_exe = "ffmpeg"

total_orig_bytes = 0
total_new_bytes = 0

for idx, rel_path in enumerate(matches, 1):
    # Convert media/... to OS path
    sub_path = rel_path[len("media/"):].replace("/", os.sep)
    src_file = os.path.join(website_dir, "media", sub_path)
    dst_file = os.path.join(web_media_dir, sub_path)
    
    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
    
    if not os.path.exists(src_file):
        print(f"[{idx}/{len(matches)}] MISSING: {src_file}")
        continue
        
    orig_size = os.path.getsize(src_file)
    total_orig_bytes += orig_size
    ext = os.path.splitext(src_file)[1].lower()
    
    if ext == ".mp4":
        # Check if already compressed and valid
        if os.path.exists(dst_file) and os.path.getsize(dst_file) > 10000:
            new_size = os.path.getsize(dst_file)
            total_new_bytes += new_size
            print(f"[{idx}/{len(matches)}] SKIP (exists): {rel_path} ({orig_size/1024/1024:.1f}MB -> {new_size/1024/1024:.1f}MB)")
            continue
            
        print(f"[{idx}/{len(matches)}] Compressing video: {rel_path} ({orig_size/1024/1024:.1f}MB)...", flush=True)
        # Scale down to max height 720p (keeping aspect ratio divisible by 2), 30fps, H.264 CRF 28, AAC 96k, faststart
        cmd = [
            ffmpeg_exe, "-y", "-i", src_file,
            "-vf", "scale='min(1280,iw)':-2",
            "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-maxrate", "1800k", "-bufsize", "3600k",
            "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart",
            dst_file
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f"  ERROR compressing {src_file}: {res.stderr.decode('utf-8', errors='ignore')[-300:]}")
        else:
            new_size = os.path.getsize(dst_file)
            total_new_bytes += new_size
            print(f"  -> Done: {orig_size/1024/1024:.1f}MB -> {new_size/1024/1024:.1f}MB ({new_size/orig_size*100:.1f}%)", flush=True)
    else:
        # Image: compress via ffmpeg to max 1600px width, quality 4
        if not os.path.exists(dst_file):
            cmd = [
                ffmpeg_exe, "-y", "-i", src_file,
                "-vf", "scale='min(1600,iw)':-2",
                "-q:v", "4",
                dst_file
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode != 0 or not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)
        new_size = os.path.getsize(dst_file)
        total_new_bytes += new_size
        print(f"[{idx}/{len(matches)}] Image optimized: {rel_path} ({orig_size/1024/1024:.1f}MB -> {new_size/1024/1024:.2f}MB)", flush=True)

print("="*60)
print(f"TOTAL ORIGINAL: {total_orig_bytes/1024/1024:.1f} MB")
print(f"TOTAL WEB-DIET: {total_new_bytes/1024/1024:.1f} MB")
print(f"REDUCTION: {(1 - total_new_bytes/max(1, total_orig_bytes))*100:.1f}% saved!")
