# 符号映射

先运行../user_code/practice.py。三个主要符号在runtime.py：

- split_history：checked_exchange验证每组请求ID与结果一一对应，再分旧组和近期组；全部用副本。
- trim_results：先要求归档收据，只替换旧组大正文，保留原ID/is_error及近期组。
- prepare_context：先校验/检查字节预算，归档→廉价移出→必要时有界摘要→候选协议与大小复查；返回后才允许循环提交。
- history_bytes：JSON UTF-8字节计量，不是tokenizer。
- archive_writer：写JSONL压缩前快照，最多1MB，独占创建不覆盖，成功关闭后给收据。
- summarize_claude：普通Messages SDK生成摘要，必须end_turn且全为text；摘要长度由prepare_context再检查。

唯一循环仍s01/core/runtime.py，新增可选prepare参数。prepare深副本输入；异常/非list返回context_error，父calls不增加；成功切片替换原messages对象，ask/execute接口不变。未传prepare时旧行为不变。按符号断点，不固定行号。
