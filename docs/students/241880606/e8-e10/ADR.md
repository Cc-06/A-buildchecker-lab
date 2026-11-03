# 决策记录

背景与约束：
EChecker需要决定何时复用历史依赖图，何时刷新。受限于教学环境，使用 gcc -MM 和 BuildChecker 进行实际依赖采集。

选择与替代方案：
A：缓存失效条件绑定预处理指令、配方、CFLAGS和编译器身份。任何配置变化均保守刷新。
替代方案：只按源码 mtime 判断会漏头文件间接 include 或配置变化。

代价与覆盖范围：
保守刷新可能多采集无用的目标，但保证不漏边。未覆盖复杂的动态系统调用归并和递归包含。

验证命令与实际证据：
E10 测试了 30 次完整集合对比，`results.csv` 全为 `equal=True`。`include`、`flags`、`header` 场景成功触发 refreshed=2；`unchanged/body/declaration` 场景 reused=2。
