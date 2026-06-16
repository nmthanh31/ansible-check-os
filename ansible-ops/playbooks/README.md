# Playbooks

| Playbook | Mục đích |
|---|---|
| `check_all.yml` | Chạy toàn bộ job kiểm tra OS và Kubernetes |
| `check_os.yml` | Chạy `JOB-OS-01` đến `JOB-OS-04` |
| `check_kubernetes.yml` | Chạy `JOB-K8S-01` đến `JOB-K8S-03` |

## Ghi chú

- `check_os.yml` chạy trên group `kubernetes_servers`.
- `check_kubernetes.yml` chạy từ node đầu tiên trong group `kubernetes_servers`
  để gọi Kubernetes API hoặc `kubectl`.
- Các playbook `audit_*` cũ chưa bị xóa nhưng không còn là luồng chính.
