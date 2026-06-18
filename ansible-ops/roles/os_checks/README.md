# Role `os_checks`

Role này chứa các job kiểm tra OS theo `list-job.md`.

| File task | Job |
|---|---|
| `job_os_01_node_resources.yml` | `JOB-OS-01` - Kiểm tra tài nguyên node |
| `job_os_02_event_logs.yml` | `JOB-OS-02` - Kiểm tra event log OS |
| `job_os_03_cron_jobs.yml` | `JOB-OS-03` - Kiểm tra cron job OS |
| `job_os_04_smart.yml` | `JOB-OS-04` - Kiểm tra SMART |

`JOB-OS-04` phải skip khi target là VM không expose SMART.

## Tags

| Tag | Chay phan nao |
|---|---|
| `os` | Toan bo role OS tu playbook |
| `checks` | Tat ca role kiem tra |
| `job_os_01` / `os_resources` | Chi `JOB-OS-01` |
| `job_os_02` / `os_event_logs` | Chi `JOB-OS-02` |
| `job_os_03` / `os_cron_jobs` | Chi `JOB-OS-03` |
| `job_os_04` / `os_smart` | Chi `JOB-OS-04` |
| `os_report` | Phan ghi report OS |

Vi `save_report.yml` co tag `always`, khi chay rieng mot job thi report van
duoc ghi lai. Cac job khong chay trong lan do se khong co du lieu moi.
