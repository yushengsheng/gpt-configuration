#!/usr/bin/env python3
"""将仓库中的第三方技能安装到当前用户的 Codex 技能目录。"""

import argparse
import filecmp
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def identical(source, target):
    if target.is_symlink() or not target.is_dir():
        return False
    source_items = {p.relative_to(source): p for p in source.rglob("*")}
    target_items = {p.relative_to(target): p for p in target.rglob("*")}
    if source_items.keys() != target_items.keys():
        return False
    for relative, original in source_items.items():
        installed = target_items[relative]
        if installed.is_symlink() or original.is_dir() != installed.is_dir():
            return False
        if original.is_file() and not filecmp.cmp(original, installed, shallow=False):
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.home() / ".agents" / "skills",
                        help="安装目录，默认为 ~/.agents/skills")
    parser.add_argument("--force", action="store_true", help="备份后替换已有的同名技能")
    args = parser.parse_args()

    source_root = Path(__file__).resolve().parent / "skills"
    target = args.target.expanduser().resolve()
    if source_root == target or source_root in target.parents or target in source_root.parents:
        parser.error("安装目录不能与仓库的 skills 目录重叠。")
    skills = sorted(p for p in source_root.iterdir() if (p / "SKILL.md").is_file())
    if not skills:
        parser.error("仓库中未找到技能。")
    if any(p.is_symlink() for skill in skills for p in [skill, *skill.rglob("*")]):
        parser.error("源技能含符号链接，请先将所需文件保存到仓库。")

    plans = [(skill, target / skill.name) for skill in skills]
    changed = [(skill, dest) for skill, dest in plans if not identical(skill, dest)]
    conflicts = [skill.name for skill, dest in changed if dest.exists() or dest.is_symlink()]
    if conflicts and not args.force:
        parser.error("同名技能已有不同内容：" + "、".join(conflicts) +
                     "。本次未安装；使用 --force 可备份后替换。")

    target.mkdir(parents=True, exist_ok=True)
    backup_root = target.parent / (target.name + "-backups") / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for skill, dest in changed:
        # 先完成复制，再移动旧版本，避免复制失败影响已有技能。
        with tempfile.TemporaryDirectory(prefix=".skill-install-", dir=target.parent) as staging:
            staged = Path(staging) / skill.name
            shutil.copytree(skill, staged)
            backup = None
            if dest.exists() or dest.is_symlink():
                backup_root.mkdir(parents=True, exist_ok=True)
                backup = backup_root / skill.name
                dest.rename(backup)
            try:
                staged.rename(dest)
            except OSError:
                if backup is not None:
                    backup.rename(dest)
                raise
        suffix = "（旧版本已备份）" if backup is not None else ""
        print("已安装：" + skill.name + suffix)

    unchanged = len(plans) - len(changed)
    if unchanged:
        print(f"内容相同，保留现有技能：{unchanged} 个。")
    print("完成。如 Codex 中未出现技能，请重新启动 Codex。")


if __name__ == "__main__":
    try:
        main()
    except OSError:
        print("安装失败：请检查目录权限、磁盘空间和文件是否被占用。", file=sys.stderr)
        sys.exit(1)
