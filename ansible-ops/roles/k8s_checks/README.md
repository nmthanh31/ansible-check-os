# Role `k8s_checks`

Role nay chua cac job kiem tra Kubernetes.
Moi job tu tao report cua chinh no, in ra terminal bang `ansible.builtin.debug`
va ghi JSON rieng vao `artifacts/k8s/<control-plane-host>/`.

Khong dung `save_report.yml` gom chung nua. Report duoc ghi ngay trong tung job
de khi chay rieng tag nao thi co file cua dung job do.

| File task | Job |
|---|---|
| `job_k8s_01_resources.yml` | `JOB-K8S-01` - Kiem tra tai nguyen |
| `job_k8s_02_events.yml` | `JOB-K8S-02` - Kiem tra event toan cum |
| `job_k8s_03_alerts.yml` | `JOB-K8S-03` - Kiem tra va tao canh bao |

## Tags

| Tag | Chay phan nao |
|---|---|
| `kubernetes` | Toan bo role Kubernetes tu playbook |
| `checks` | Tat ca role kiem tra |
| `job_k8s_01` / `k8s_resources` | Chi `JOB-K8S-01` |
| `job_k8s_02` / `k8s_events` | Chi `JOB-K8S-02` |
| `job_k8s_03` / `k8s_alerts` | Chi `JOB-K8S-03` |

Luu y: `JOB-K8S-03` can du lieu tu `JOB-K8S-01` va `JOB-K8S-02`.
Neu chay rieng `job_k8s_03`, report co the la `skipped` hoac thieu ngu canh.

## Output

```text
artifacts/
`-- k8s/
    `-- <control-plane-host>/
        |-- job_k8s_01_resources.json
        |-- job_k8s_02_events.json
        `-- job_k8s_03_alerts.json
```
