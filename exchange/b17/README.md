# B17 → A17 E13 项目交换包

提供者：B17 邢蓁儿，251880498。接收者：A17。
本包是 B17 在课程历史项目上维护的适配副本，不是教师三项目包。
准确来源、原始提交和适配提交见 manifest.json；project.bundle 包含适配仓库历史。
不能用主仓库 URL 直接获取适配 SHA；请从本包克隆。

## A17 怎么运行

在你们自己的 Linux E11–E12 仓库根目录操作。将本包全部文件放到
data/e13-b17-251880498/，然后执行：

```bash
git bundle verify data/e13-b17-251880498/project.bundle
git clone data/e13-b17-251880498/project.bundle data/e13-b17-251880498/repo
python3 run_e11e12.py run --request data/e13-b17-251880498/request-e11-a.json --out work/e13-B17-on-A17-01
echo "EXIT_CODE=$?"
```

输出目录如已存在，换一个新编号。请求中的 /course 是运行入口的容器挂载路径。
mode=e11-a 运行你们负责的全量/增量检测。构建和输出说明供后续 B 端修复验证使用。
正常 make app 后 ./app 输出 VALUE=1。将 config.h 中 VALUE 从 1 改成 2 后，
修复前目标可能仍输出 VALUE=1；正确补齐 config.h 依赖后应输出 VALUE=2。
仅在隔离副本中做修改，保留原仓库提交。
candidate.Dockerfile 使用原 B17 云机的软件源配置；若网络不可达，保留失败日志，
另存候选并记录字节 SHA 后重试，不覆盖原候选。

## 请 A17 返回

1. A17 系统仓库 URL、完整系统提交 SHA、实际请求及退出码。
2. 完整 work/e13-B17-on-A17-01/ 目录，含 result.json、incremental-check.json、
   报告引用的产物及原始日志；保持字节不变，不只发截图。
3. job_id、trace_id、base/target 完整 SHA、报告和产物 SHA256。
4. 问题及对应 Issue/MR 链接。

同时请提供 A17 自己维护的项目包（仓库/历史、base/target SHA、Dockerfile、
预期输出、运行限制、请求）。若 B17 接下来修复 A17 项目，
请另给 A17 检测该 A17 项目同一个 target SHA 的当次完整结果目录。
本包不包含 A17 已执行的证明，不能据此填写跨组 C1–C8 通过。
