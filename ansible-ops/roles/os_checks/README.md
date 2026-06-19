# Role `os_checks`

Role nay chua cac job kiem tra OS theo `list-job.md`.
Moi job tu tao report cua chinh no, in ra terminal bang `ansible.builtin.debug`
va ghi JSON rieng vao `artifacts/os/<host>/`.

Khong dung `save_report.yml` gom chung nua. Report duoc ghi ngay trong tung job
de khi chay rieng tag nao thi co file cua dung job do.

| File task | Job |
|---|---|
| `job_os_01_node_resources.yml` | `JOB-OS-01` - Kiem tra tai nguyen node |
| `job_os_02_event_logs.yml` | `JOB-OS-02` - Kiem tra event log OS |
| `job_os_03_cron_jobs.yml` | `JOB-OS-03` - Kiem tra cron job OS |
| `job_os_04_smart.yml` | `JOB-OS-04` - Kiem tra SMART |

## Tags

| Tag | Chay phan nao |
|---|---|
| `os` | Toan bo role OS tu playbook |
| `checks` | Tat ca role kiem tra |
| `job_os_01` / `os_resources` | Chi `JOB-OS-01` |
| `job_os_02` / `os_event_logs` | Chi `JOB-OS-02` |
| `job_os_03` / `os_cron_jobs` | Chi `JOB-OS-03` |
| `job_os_04` / `os_smart` | Chi `JOB-OS-04` |

## Output

```text
artifacts/
`-- os/
    `-- <host>/
        |-- job_os_01_node_resources.json
        |-- job_os_02_event_logs.json
        |-- job_os_03_cron_jobs.json
        `-- job_os_04_smart.json
```
