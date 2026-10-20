请求一_贸易条件推演

理论条文分流；实际调用候选registry提取ZG8_TRADE，在线核读ZG-8贸易正文。未起盘。

任务领域只读范围为候选SKILL/references/scripts/assets及指定evals/fixtures/hosted.json；未读禁区评估材料，不安装、不改技能、不Git、不向外部应用写入。古籍Web为正文只读，实录见上级web_calls_primary*.json。启动通用技能读取单列在上级access_record.md。

冻结前source_hashes_before.json与初次patterns/calls保留。收到root冻结通知后重读当前空墓与应期.md，保存source_hashes_frozen_start.json；最终32项领域源码起止哈希一致，详见run_integrity.json。

真实程序调用（逐次保留，不以说明代替执行）：
- ["C:\\Users\\Euell\\.codex\\skills\\qimen-jiepan\\.venv\\Scripts\\python.exe", "-B", "-c", "import sys,json; sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0,'X:\\\\Daily\\\\奇门\\\\qimen-jiepan-rewrite-20261019\\\\qimen-jiepan-skill\\\\scripts'); from rule_evaluator import registry; print(json.dumps(next(m for m in registry()['methods'] if m['id']=='ZG8_TRADE'),ensure_ascii=False,indent=2))"]；UTC 2026-10-20T12:43:40.467934+00:00 至 2026-10-20T12:43:40.785775+00:00；退出码 0；输出 method_lookup.stdout.txt；错误 method_lookup.stderr.txt。

本题产物原始字节SHA-256：
- answer.md：2808a5556849327cd090e51076b101d136d8b109875db66c307d6f47ebca5f3b
- calls.json：e6d6673624ad6c8c9a48311281ae5b9f279ad7e4d440e4914aebb5f338e42368
- method_lookup.stderr.txt：e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- method_lookup.stdout.txt：3acba9258165b839bdb44d6dcad9a3a2415d0113cd533c8166c5fb89df0d37eb
- method_used.json：3acba9258165b839bdb44d6dcad9a3a2415d0113cd533c8166c5fb89df0d37eb
- record.json：ce77ff95d2b55388fc7d974f13123683886dbf76c6ba4abdcb587c1e594d3149
