# Ansible Checks

Khung du an dung de kiem tra OS va Kubernetes cho cac VM trong moi truong `lab`.

Nguon danh sach job: `../list-job.md`.

## Luong chinh

```text
Inventory
  -> prepare_tools.yml
     -> roles/tool_prerequisites
        -> Kiem tra/cai cong cu can thiet cho cac job sau
  -> check_os.yml
     -> roles/os_checks
        -> JOB-OS-01: Kiem tra tai nguyen node
        -> JOB-OS-02: Kiem tra event log OS
        -> JOB-OS-03: Kiem tra cron job OS
        -> JOB-OS-04: Kiem tra SMART
  -> check_kubernetes.yml
     -> roles/k8s_checks
        -> JOB-K8S-01: Kiem tra tai nguyen
        -> JOB-K8S-02: Kiem tra event toan cum
        -> JOB-K8S-03: Kiem tra va tao canh bao
  -> terminal output + artifacts/
  -> scripts/format_reports.py
     -> artifacts/report.md
```

`check_*` chi doc du lieu, in report ngan ra terminal va ghi JSON report theo tung job
vao `artifacts/`, khong thay doi cau hinh he thong. Sau khi chay `check_all.yml`,
file bao cao de doc duoc tao tai `artifacts/report.md`.
Rieng `prepare_tools.yml` co the cai package thieu, nen duoc tach rieng va chay
co chu dich truoc khi kiem tra.

## Playbook su dung

| Playbook | Muc dich |
|---|---|
| `playbooks/prepare_tools.yml` | Kiem tra/cai cong cu can thiet truoc khi chay job |
| `playbooks/check_os.yml` | Chay cac job OS |
| `playbooks/check_kubernetes.yml` | Chay cac job Kubernetes |
| `playbooks/check_all.yml` | Chay toan bo job kiem tra OS va Kubernetes |

`check_kubernetes.yml` chay tren node dau tien cua group
`kubernetes_control_plane`, vi control-plane co `kubectl`/kubeconfig de goi
Kubernetes API. Mac dinh role dung:

```text
/var/lib/rancher/rke2/bin/kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml
```

## Prepare tools

Chay playbook nay neu job bi skip vi thieu cong cu, vi du `smartctl` cho SMART:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=roles \
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass -v
```

Neu chay trong WSL tu thu muc `/mnt/c` hoac `/mnt/d`, Ansible co the bo qua
`ansible.cfg` vi thu muc bi xem la world-writable. Khi do truyen ro config va
inventory:

```bash
ANSIBLE_CONFIG="$PWD/ansible.cfg" \
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml \
--ask-vault-pass
```

Sau khi chay xong, doc bao cao tong hop tai:

```text
artifacts/report.md
```

Neu chi muon chay cac task check command, khong cai package:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=roles \
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass --tags tool_check -v
```

Neu chi muon chuan bi SMART tool:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=roles \
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass --tags smart_tools -v
```

## Cay thu muc chinh

```text
ansible-ops/
|-- ansible.cfg
|-- inventories/
|   `-- lab/
|-- playbooks/
|   |-- prepare_tools.yml
|   |-- check_all.yml
|   |-- check_os.yml
|   |-- check_kubernetes.yml
|   `-- format_report.yml
|-- scripts/
|   `-- format_reports.py
|-- artifacts/
|   |-- report.md
|   |-- os/
|   |   `-- <host>/
|   |       |-- job_os_01_node_resources.json
|   |       |-- job_os_02_event_logs.json
|   |       |-- job_os_03_cron_jobs.json
|   |       `-- job_os_04_smart.json
|   `-- k8s/
|       `-- <control-plane-host>/
|           |-- job_k8s_01_resources.json
|           |-- job_k8s_02_events.json
|           `-- job_k8s_03_alerts.json
|-- roles/
|   |-- tool_prerequisites/
|   |-- os_checks/
|   `-- k8s_checks/
```

## Nguyen tac

- Dung `changed_when: false` cho cac task chi kiem tra.
- Thieu Metrics Server hoac monitoring stack khong duoc lam dung job.
- Thieu `smartctl` hoac VM khong expose SMART phai ghi `skipped`.
- Neu muon cap cong cu thieu nhu `smartctl`, chay `prepare_tools.yml` truoc.
- Credential phai luu bang Ansible Vault hoac secret manager.
- Khong luu password trong inventory.
