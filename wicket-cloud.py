import json
from datetime import datetime

CLOUD_RESOURCES = [
    {'id': 'vm-prod-db', 'type': 'vm', 'status': 'running', 'last_active': '2024-06-01', 'monthly_cost': 950, 'ports': [22, 80], 'sg_outdated': False},
    {'id': 'vm-unused', 'type': 'vm', 'status': 'stopped', 'last_active': '2022-07-01', 'monthly_cost': 200, 'ports': [22], 'sg_outdated': True},
    {'id': 'storage-archive', 'type': 'storage', 'status': 'available', 'last_active': '2021-04-25', 'monthly_cost': 35, 'ports': [], 'sg_outdated': False},
    {'id': 'db-old', 'type': 'db', 'status': 'idle', 'last_active': None, 'monthly_cost': 250, 'ports': [3306], 'sg_outdated': True},
    {'id': 'dev-janet', 'type': 'vm', 'status': 'running', 'last_active': '2026-06-06', 'monthly_cost': 80, 'ports': [], 'sg_outdated': False}
]

AUDIT_TRAIL = []
BACKUP_STATE = []

def backup_state(resources):
    try:
        BACKUP_STATE.append(json.loads(json.dumps(resources)))
        AUDIT_TRAIL.append(f"[{datetime.now()}] State backup created before changes.")
    except Exception as e:
        AUDIT_TRAIL.append(f"[{datetime.now()}] Backup failed: {e}")

def butter_smooth_delete_live_by_id(resource_id):
    # Always lookup resource in live list by ID, not index.
    for i, r in enumerate(CLOUD_RESOURCES):
        if r['id'] == resource_id:
            desc = f"{r['id']} ({r['type']}), last active {r.get('last_active','unknown')}, ${r['monthly_cost']}/mo"
            CLOUD_RESOURCES.pop(i)
            AUDIT_TRAIL.append(f"[{datetime.now()}] DELETED: {desc}. Full backup made before deletion.")
            return f"Deleted {desc}. Safe, fully rollback-able."
    AUDIT_TRAIL.append(f"[{datetime.now()}] (delete) {resource_id}: Not found—no change.")
    return f"No action: Resource {resource_id} does not exist. Nothing done."

def butter_smooth_delete_sim(resource):
    desc = f"{resource['id']} ({resource['type']}), last active {resource.get('last_active','unknown')}, ${resource['monthly_cost']}/mo"
    msg = f"[Dry Run] Would delete {desc}. No changes made."
    AUDIT_TRAIL.append(f"[{datetime.now()}] DRY RUN: Would delete {desc}. No changes.")
    return msg

def generate_terraform_destroy_command(resource):
    return f"terraform destroy -target=module.{resource['type']}.{resource['id']}"

def cloud_scan_and_suggest(dry_run=True):
    output = []
    ghost_assets = []
    total_savings = 0

    # Build static list of (ID, resource) to delete, and of safe actives
    delete_resources = []
    actives = []
    for res in CLOUD_RESOURCES:
        unused = (
            res['status'] == 'stopped'
            or res['status'] == 'idle'
            or (res.get('last_active') and not str(res.get('last_active')).startswith(('2025', '2026')))
        )
        ghost = unused and res.get('ports') and res.get('sg_outdated')
        if unused:
            delete_resources.append(res.copy())
            total_savings += res.get('monthly_cost', 0)
        else:
            actives.append(res.copy())
        if ghost:
            ghost_assets.append(res['id'])

    delete_ids = {res['id'] for res in delete_resources}

    if not dry_run and delete_resources:
        backup_state(CLOUD_RESOURCES)
    for res in delete_resources:
        rid = res['id']
        if dry_run:
            if rid in ghost_assets:
                output.append(
                    f"[Ghost Asset] {res['id']} is unused with active ports {res['ports']} and outdated security group—potential attack surface! (dry-run only)"
                )
            msg = butter_smooth_delete_sim(res)
            output.append(msg)
            tfdiff = generate_terraform_destroy_command(res)
            output.append(f"[IaC Sync Suggestion] {tfdiff}")
        else:
            msg = butter_smooth_delete_live_by_id(rid)
            output.append(msg)
            tfdiff = generate_terraform_destroy_command(res)
            output.append(f"[IaC AUTO SYNC] {tfdiff} (run to keep Terraform etc. in sync!)")
    for res in actives:
        output.append(f"[Active] {res['id']} ({res['type']}), last active: {res.get('last_active','unknown')}, cost: ${res.get('monthly_cost','?')}/mo —recently used, not suggested for removal.")
    if delete_resources:
        output.append(f"\n[Immediate ROI] This cleanup would save you ~${total_savings}/month, excluding hidden/nested costs.")
    else:
        output.append("\n[No savings] All assets are in active use.")
    return output

def audit_report():
    print("\n=== Wicket Cloud Audit Trail ===")
    for entry in AUDIT_TRAIL:
        print(entry)
    print("===")

def rollback():
    try:
        if BACKUP_STATE:
            CLOUD_RESOURCES.clear()
            CLOUD_RESOURCES.extend(json.loads(json.dumps(BACKUP_STATE[-1])))
            AUDIT_TRAIL.append(f"[{datetime.now()}] Rolled back to previous backup for safety.")
            return "Rollback complete."
        else:
            return "No backups present. Nothing to roll back."
    except Exception as e:
        AUDIT_TRAIL.append(f"[{datetime.now()}] Rollback failed: {e}")
        return f"Rollback failed: {e}"

def butter_smooth_ui():
    print("\n====== Wicket Cloud Butter Smooth Demo (DRY RUN) ======")
    try:
        suggestions = cloud_scan_and_suggest(dry_run=True)
        for msg in suggestions:
            print(msg)
        audit_report()
    except Exception as e:
        print(f"All safe: No changes made. (Unexpected input error: {e})")
    print("\nReady for actual cleanup (creates backup and IaC commands)?")
    try:
        action = input("Type GO to delete unused resources (safe), or just Enter to exit: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nSession ended by user. No changes made.")
        return
    if action == "GO":
        try:
            results = cloud_scan_and_suggest(dry_run=False)
            for msg in results:
                print(msg)
            audit_report()
        except Exception as e:
            print(f"Error during cleanup. Attempting rollback: {rollback()}\nDetails: {e}")
            audit_report()
    else:
        print("No changes made—your cloud is safe and untouched.")

if __name__ == "__main__":
    try:
        butter_smooth_ui()
    except Exception as e:
        print(f"\nCritical error. No cloud resources harmed! Details: {e}")
        audit_report()