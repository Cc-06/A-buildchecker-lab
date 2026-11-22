# CI 运行记录

仓库：https://github.com/Cc-06/A-buildchecker-lab；草稿 PR：https://github.com/Cc-06/A-buildchecker-lab/pull/6。

实现提交 `bf0a08c34e276266ed880e27caa702b5010231d4` 的 push 检查全部通过：

| 检查 | 状态 | 运行链接 |
| --- | --- | --- |
| E7 A quality gate | success | https://github.com/Cc-06/A-buildchecker-lab/actions/runs/45046746556 |
| E8–E10 teaching validation | success | https://github.com/Cc-06/A-buildchecker-lab/actions/runs/45046746615 |
| E11 A integration | success | https://github.com/Cc-06/A-buildchecker-lab/actions/runs/45046746623 |
| E13–E14 integration gate | success | https://github.com/Cc-06/A-buildchecker-lab/actions/runs/45046746560 |

E13/E14 的 contracts 与 four-services 都通过；four-services 实际执行固定样例、B17 项目、HTTP 旧报告/哈希/错误补丁门禁、假 Key 扫描和真实运行验证容器超时清理，不只做静态 Compose 检查。

首次 `3217b076a71878795d6a5bd4a0e074ed0c37054d` 的 CI 因 root 容器与 GitHub runner 目录所有权不同，在 EChecker 触发 Git dubious ownership。已增加 Compose UID/GID/socket组配置，使用宿主身份运行；保留失败日志 `ci-first-failure.log`，没有关闭 Git 保护。

同一修复后 push 回归全部通过，但 PR 事件中的进程清理测试读取 `/proc/<pid>/stat` 时遇到进程刚好消失的竞态（ProcessLookupError）。这是测试观测竞态；现对“进程已不存在”明确视为退出，同时保留对进程仍运行的失败断言。未取消子进程清理测试。

最终文档/测试提交的 push 和 PR 检查会再次运行。最终交付包 `evidence/e14-evidence/current-head-ci.json` 保存该最终 HEAD 的全部实际状态、结论、运行链接和 job 详情；`VERSION.json` 保存最终 HEAD。对当前远端状态可直接查看 PR #6 的 Checks。报告不把前一次通过记录冒充另一次运行。

CI 通过仅是发布门禁之一，不能替代 B17 独立回测、教师隐藏测试与人工评审合并。当前仍为候选待发布。
