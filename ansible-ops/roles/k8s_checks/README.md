# Role `k8s_checks`

Role này chứa các job kiểm tra Kubernetes:

| File task | Job |
|---|---|
| `job_k8s_01_resources.yml` | `JOB-K8S-01` - Kiểm tra tài nguyên |
| `job_k8s_02_events.yml` | `JOB-K8S-02` - Kiểm tra event toàn cụm |
| `job_k8s_03_alerts.yml` | `JOB-K8S-03` - Kiểm tra và tạo cảnh báo |

Kết quả JSON được lưu về máy control tại `artifacts/kubernetes-check.json`.
