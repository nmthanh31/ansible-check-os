# Playbooks

| Playbook | Muc dich |
|---|---|
| `prepare_tools.yml` | Kiem tra/cai package can thiet cho cac job sau |
| `check_all.yml` | Chay toan bo job kiem tra OS va Kubernetes |
| `check_os.yml` | Chay `JOB-OS-01` den `JOB-OS-04` |
| `check_kubernetes.yml` | Chay `JOB-K8S-01` den `JOB-K8S-03` |

## Ghi chu

- `prepare_tools.yml` chay tren group `kubernetes_servers` va co the cai package
  thieu nhu `smartmontools`.
- `check_os.yml` chay tren group `kubernetes_servers`.
- `check_kubernetes.yml` chay tu node dau tien trong group
  `kubernetes_control_plane` de goi Kubernetes API hoac `kubectl`.
- Cac worker khong chay `kubectl`; khi can du lieu runtime, role co the delegate
  task nhu `crictl stats` sang tung node trong `kubernetes_servers`.

## Lenh chay

Chuan bi cong cu, co cai package:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=roles \
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass -v
```

Chi kiem tra cong cu, khong cai:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=roles \
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass --tags tool_check -v
```

Chi chuan bi SMART tool:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=roles \
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass --tags smart_tools -v
```

## Tags chay rieng

| Tag | Lenh mau |
|---|---|
| `prepare_tools` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml --ask-vault-pass --tags prepare_tools` |
| `os` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml --ask-vault-pass --tags os` |
| `kubernetes` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml --ask-vault-pass --tags kubernetes` |
| `tool_check` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml --ask-vault-pass --tags tool_check` |
| `smart_tools` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml --ask-vault-pass --tags smart_tools` |
| `job_os_01` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_os.yml --ask-vault-pass --tags job_os_01` |
| `job_os_02` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_os.yml --ask-vault-pass --tags job_os_02` |
| `job_os_03` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_os.yml --ask-vault-pass --tags job_os_03` |
| `job_os_04` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_os.yml --ask-vault-pass --tags job_os_04` |
| `job_k8s_01` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_kubernetes.yml --ask-vault-pass --tags job_k8s_01` |
| `job_k8s_02` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_kubernetes.yml --ask-vault-pass --tags job_k8s_02` |
| `job_k8s_03` | `ansible-playbook -i inventories/lab/inventory.ini playbooks/check_kubernetes.yml --ask-vault-pass --tags job_k8s_03` |
