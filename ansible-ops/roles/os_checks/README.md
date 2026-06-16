# Role `os_checks`

Role này chứa các job kiểm tra OS theo `list-job.md`.

| File task | Job |
|---|---|
| `job_os_01_node_resources.yml` | `JOB-OS-01` - Kiểm tra tài nguyên node |
| `job_os_02_event_logs.yml` | `JOB-OS-02` - Kiểm tra event log OS |
| `job_os_03_cron_jobs.yml` | `JOB-OS-03` - Kiểm tra cron job OS |
| `job_os_04_smart.yml` | `JOB-OS-04` - Kiểm tra SMART |

`JOB-OS-04` phải skip khi target là VM không expose SMART.
