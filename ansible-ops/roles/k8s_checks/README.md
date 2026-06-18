# Role `k8s_checks`

Role này chứa các job kiểm tra Kubernetes:

| File task | Job |
|---|---|
| `job_k8s_01_resources.yml` | `JOB-K8S-01` - Kiểm tra tài nguyên |
| `job_k8s_02_events.yml` | `JOB-K8S-02` - Kiểm tra event toàn cụm |
| `job_k8s_03_alerts.yml` | `JOB-K8S-03` - Kiểm tra và tạo cảnh báo |

Kết quả JSON được lưu về máy control trong `artifacts/k8s/`.

## Tags

| Tag | Chay phan nao |
|---|---|
| `kubernetes` | Toan bo role Kubernetes tu playbook |
| `checks` | Tat ca role kiem tra |
| `job_k8s_01` / `k8s_resources` | Chi `JOB-K8S-01` |
| `job_k8s_02` / `k8s_events` | Chi `JOB-K8S-02` |
| `job_k8s_03` / `k8s_alerts` | Chi `JOB-K8S-03` |
| `k8s_report` | Phan ghi report Kubernetes |

Luu y: `JOB-K8S-03` can du lieu tu `JOB-K8S-01` va `JOB-K8S-02`.
Neu chay rieng `job_k8s_03`, alert co the thieu ngu canh.
