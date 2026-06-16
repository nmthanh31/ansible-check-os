# Ansible Checks

Khung dự án hiện tập trung vào kiểm tra OS và Kubernetes cho 6 VM trong môi
trường `lab`.

Nguồn danh sách job: `../list-job.md`.

## Luồng chính

```text
Inventory
  -> check_os.yml
     -> roles/os_checks
        -> JOB-OS-01: Kiểm tra tài nguyên node
        -> JOB-OS-02: Kiểm tra event log OS
        -> JOB-OS-03: Kiểm tra cron job OS
        -> JOB-OS-04: Kiểm tra SMART
  -> check_kubernetes.yml
     -> roles/k8s_checks
        -> JOB-K8S-01: Kiểm tra tài nguyên
        -> JOB-K8S-02: Kiểm tra event toàn cụm
        -> JOB-K8S-03: Kiểm tra và tạo cảnh báo
  -> Report
```

Các job chỉ đọc dữ liệu và tạo báo cáo, không thay đổi cấu hình hệ thống.

## Cây thư mục chính

```text
ansible-ops/
|-- ansible.cfg
|-- inventories/
|   `-- lab/
|-- playbooks/
|   |-- check_all.yml
|   |-- check_os.yml
|   `-- check_kubernetes.yml
|-- roles/
|   |-- os_checks/
|   |   |-- defaults/main.yml
|   |   `-- tasks/
|   |       |-- main.yml
|   |       |-- job_os_01_node_resources.yml
|   |       |-- job_os_02_event_logs.yml
|   |       |-- job_os_03_cron_jobs.yml
|   |       `-- job_os_04_smart.yml
|   |-- k8s_checks/
|   |   |-- defaults/main.yml
|   |   `-- tasks/
|   |       |-- main.yml
|   |       |-- job_k8s_01_resources.yml
|   |       |-- job_k8s_02_events.yml
|   |       `-- job_k8s_03_alerts.yml
|   `-- report/
|-- artifacts/
`-- docs/
```

## Playbook sử dụng

| Playbook | Mục đích |
|---|---|
| `playbooks/check_os.yml` | Chạy các job OS |
| `playbooks/check_kubernetes.yml` | Chạy các job Kubernetes |
| `playbooks/check_all.yml` | Chạy toàn bộ job kiểm tra |

Các playbook `audit_*` và role cũ hiện không còn là luồng chính. Chúng được giữ
lại để tham khảo hoặc tái sử dụng code khi cần.

## Nguyên tắc

- Dùng `changed_when: false` cho các task kiểm tra.
- Thiếu Metrics Server hoặc monitoring stack không được làm dừng job.
- Thiếu `smartctl` hoặc VM không expose SMART phải ghi `skipped`.
- Credential phải lưu bằng Ansible Vault hoặc secret manager.
- Không lưu password trong inventory hoặc artifact báo cáo.
