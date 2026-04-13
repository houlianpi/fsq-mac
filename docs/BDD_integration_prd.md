# BDD_integration_prd

## backgroup

- 我们是Edge Mac team的quality team。 我们现在有大量的BDD Test Case在这： 


- 这些case都已经使用 Automation 工具已经变成了Automation test case。

- 之前的Automation的方式，采用的录制回放的方式，最终由man in the loop的方式确定录制时成功的。底层原理是通过MCP 来操作 Edge，所有的操作都被记录，并且整合到每一个BDD testcase的step 里面。

## goal

- 想用 fsq-mac 工具来完全替换掉之前的MCP的部分。
- 录制的脚本，需要以origin 的 cli 来展示。

注意事项：

-  BDD testcase 分为两个部分： .feature 文件 和 steps 实现。 希望录制的是steps的实现. feature文件是核心的测试用例，不在这次plan中。
- 现在使用的behave 测试框架。steps都是python的实现，这个部分我们可以讨论，我希望以完整的命令行来呈现。当然，我们可以找一个别的BDD测试框架。