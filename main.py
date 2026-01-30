import subprocess
import shutil
from pathlib import Path
import sys
import json
import os
import tempfile
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
GRAY = "\033[90m"
BOLD = "\033[1m"

def base_dir():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path.cwd()

def process_job(job):
    prefix, song_name, sound_path, omnimix_sound_path, dx_src, ifs_src, output_root = job

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        dx_dir = tmp / "2dx"
        ifs_dir = tmp / "ifs"
        dx_dir.mkdir()
        ifs_dir.mkdir()

        shutil.copy2(dx_src, dx_dir / dx_src.name)
        shutil.copy2(ifs_src, ifs_dir / ifs_src.name)

        for base in (sound_path, omnimix_sound_path):
            dx_file = base / prefix / f"{prefix}_pre.2dx"
            if dx_file.exists():
                subprocess.run(
                    [dx_dir / dx_src.name, dx_file],
                    cwd=dx_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                wav = dx_dir / "1.wav"
                if wav.exists() and wav.stat().st_size > 0:
                    target = output_root / song_name
                    target.mkdir(parents=True, exist_ok=True)
                    shutil.move(wav, target / "preview_auto_generator.wav")
                    return prefix, song_name, "folder", "OK"
                return prefix, song_name, "folder", "ERROR"

        ifs_file = sound_path / f"{prefix}.ifs"
        if ifs_file.exists():
            shutil.copy2(ifs_file, ifs_dir / ifs_file.name)
            subprocess.run(
                [ifs_dir / ifs_src.name, ifs_file.name],
                cwd=ifs_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            extracted = ifs_dir / prefix / f"{prefix}_pre.2dx"
            if extracted.exists():
                subprocess.run(
                    [dx_dir / dx_src.name, extracted],
                    cwd=dx_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                wav = dx_dir / "1.wav"
                if wav.exists() and wav.stat().st_size > 0:
                    target = output_root / song_name
                    target.mkdir(parents=True, exist_ok=True)
                    shutil.move(wav, target / "preview_auto_generator.wav")
                    return prefix, song_name, ".ifs archive", "OK"
            return prefix, song_name, ".ifs archive", "ERROR"

        return prefix, song_name, "-", "SKIP"

def main():
    if sys.platform == "win32":
        os.system("")

    root = base_dir()
    config_file = Path("paths.json")

    if config_file.exists():
        data = json.loads(config_file.read_text(encoding="utf-8"))
        sound_path = Path(data["sound_path"])
        omnimix_sound_path = Path(data["omnimix_sound_path"])
    else:
        sound_path = Path(input("Enter path to contents/data/sound: ").strip())
        omnimix_sound_path = Path(input("Enter path to contents/data_mods/omnimix/sound: ").strip())
        config_file.write_text(
            json.dumps(
                {
                    "sound_path": str(sound_path),
                    "omnimix_sound_path": str(omnimix_sound_path)
                },
                indent=2
            ),
            encoding="utf-8"
        )

    bms_root = Path(input("Enter path to BMS charts folder: ").strip())

    threads = os.cpu_count() or 1

    dx_src = root / "2dx_extract" / "2dx_extract.exe"
    ifs_src = root / "ifs_extract" / "ifs_extract.exe"
    output_root = Path.cwd() / "output"

    jobs = []
    for bms_folder in sorted(bms_root.iterdir()):
        if bms_folder.is_dir():
            prefix = bms_folder.name.split(" ", 1)[0]
            jobs.append(
                (
                    prefix,
                    bms_folder.name,
                    sound_path,
                    omnimix_sound_path,
                    dx_src,
                    ifs_src,
                    output_root
                )
            )

    print(CYAN + "\n=== 2dx preview extractor ===\n" + RESET)
    print(GRAY + f"Threads: {threads}\n" + RESET)

    success = skipped = errors = 0

    with ProcessPoolExecutor(max_workers=threads) as exe:
        futures = [exe.submit(process_job, job) for job in jobs]
        for f in as_completed(futures):
            prefix, name, source, status = f.result()
            print(BOLD + f"[{prefix}] {name}" + RESET)
            if status == "OK":
                print(GRAY + f"  source: {source}" + RESET)
                print(GREEN + "  status: OK" + RESET)
                success += 1
            elif status == "SKIP":
                print(YELLOW + "  status: SKIP" + RESET)
                skipped += 1
            else:
                print(GRAY + f"  source: {source}" + RESET)
                print(RED + "  status: ERROR" + RESET)
                errors += 1

    print(CYAN + "\n=== Summary ===" + RESET)
    print(GREEN + f"Success   : {success}" + RESET)
    print(YELLOW + f"Skipped   : {skipped}" + RESET)
    print(RED + f"Errors    : {errors}" + RESET)
    print(CYAN + "\nDone.\n" + RESET)
    input("Press Enter to exit...")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
