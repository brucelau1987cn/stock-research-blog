# -*- coding: utf-8 -*-
import json
import os
import sys
import subprocess
from pathlib import Path

KEYS_FILE = Path("/root/.hermes/.iwencai_keys.json")
DEFAULT_ENV_KEY = "IWENCAI_API_KEY"

def load_keys():
    if KEYS_FILE.exists():
        try:
            data = json.loads(KEYS_FILE.read_text(encoding='utf-8'))
            keys = data.get("keys", [])
            current_index = data.get("current_index", 0)
            return keys, current_index
        except Exception as e:
            print(f"[iwencai_runner] Read keys error: {e}", file=sys.stderr)
    return [], 0

def save_keys(keys, current_index):
    try:
        KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"keys": keys, "current_index": current_index}
        KEYS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f"[iwencai_runner] Save keys error: {e}", file=sys.stderr)

def rotate_key(keys, current_index):
    if not keys:
        return current_index
    new_index = (current_index + 1) % len(keys)
    save_keys(keys, new_index)
    print(f"[iwencai_runner] Key rotated: index {current_index} -> {new_index}", file=sys.stderr)
    return new_index

def run_skill_with_rotation(args):
    # args 类似: ['hithink-astock-selector', 'cli.py', '--query', '...', '--limit', '5']
    if len(args) < 2:
        print("[iwencai_runner] Usage: python3 iwencai_runner.py <slug> <script_name> [args...]", file=sys.stderr)
        sys.exit(1)
        
    slug = args[0]
    script = args[1]
    extra_args = args[2:]
    
    script_path = Path("/root/skills") / slug / "scripts" / script
    if not script_path.exists():
        # 兼容 news-search/announcement-search package-style 路径
        script_path = Path("/root/skills") / slug / "scripts" / "__main__.py"
        
    if not script_path.exists():
        print(f"[iwencai_runner] Script not found: {slug}/{script}", file=sys.stderr)
        sys.exit(1)
        
    keys, current_index = load_keys()
    
    # 尝试调用的最大次数等于 KEY 数量。如果没有配置 KEY，只尝试 1 次
    max_attempts = len(keys) if keys else 1
    
    for attempt in range(max_attempts):
        active_key = ""
        if keys:
            # 防止索引越界
            idx = current_index % len(keys)
            active_key = keys[idx]
        else:
            active_key = os.getenv(DEFAULT_ENV_KEY, "")
            
        if not active_key:
            print("[iwencai_runner] Error: No IWENCAI_API_KEY found in config or env.", file=sys.stderr)
            sys.exit(1)
            
        # 准备环境变量
        env = dict(os.environ)
        env[DEFAULT_ENV_KEY] = active_key
        
        # 准备执行指令
        cmd = ["python3", str(script_path)] + extra_args
        
        # 对于 news-search 等需要 cd 运行的包
        cwd = script_path.parent
        
        print(f"[iwencai_runner] Attempt {attempt+1}/{max_attempts} using key index {current_index if keys else 'env'}", file=sys.stderr)
        
        res = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
        
        # 检查是否由于 Key 超限或失效报错
        output_all = res.stdout + "\n" + res.stderr
        is_limit_error = any(x in output_all for x in ["limit exceed", "rate limit", "rate_limit", "次数超限", "超出限制", "429", "403", "forbidden", "key invalid", "invalid key", "拒绝访问"])
        
        # 还要判断退出码是否非零且疑似 key 问题
        if is_limit_error and keys:
            print(f"[iwencai_runner] Key error detected in output. Rotating...", file=sys.stderr)
            current_index = rotate_key(keys, current_index)
            continue
            
        # 如果没有报错，或者已经没有多余的 Key 可供轮询，直接输出结果并退出
        if res.returncode != 0:
            print(res.stderr, file=sys.stderr)
            sys.exit(res.returncode)
            
        print(res.stdout)
        return

if __name__ == '__main__':
    run_skill_with_rotation(sys.argv[1:])
