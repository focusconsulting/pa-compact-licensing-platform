#!/usr/bin/env python3
"""
gen-tf-plan.py — Interactive Terraform plan generator.

Discovers components and environments from the iac/ directory layout,
initialises Terraform if needed, prompts for any unset required variables,
then prints (and optionally runs) the plan command.

Substitute 'plan' → 'apply' in the printed command to make changes.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
IAC_DIR = SCRIPT_DIR / "iac"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def find_components() -> list[dict]:
    """Find terraform directories under iac/components/*/terraform."""
    components_root = IAC_DIR / "components"
    if not components_root.exists():
        return []
    return sorted(
        [
            {"name": d.name, "tf_dir": d / "terraform"}
            for d in components_root.iterdir()
            if (d / "terraform").is_dir()
        ],
        key=lambda c: c["name"],
    )


def find_environments() -> list[dict]:
    """Find environment/region pairs under iac/environments/<env>/<region>/."""
    envs_root = IAC_DIR / "environments"
    if not envs_root.exists():
        return []
    results = []
    for env_dir in sorted(envs_root.iterdir()):
        if not env_dir.is_dir():
            continue
        for region_dir in sorted(env_dir.iterdir()):
            if not region_dir.is_dir():
                continue
            results.append(
                {"env": env_dir.name, "region": region_dir.name, "config_dir": region_dir}
            )
    return results


# ---------------------------------------------------------------------------
# Interactive selection
# ---------------------------------------------------------------------------

def select(prompt: str, options: list, display_fn=str):
    """Numbered interactive selector. Returns the chosen item."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {display_fn(opt)}")
    while True:
        try:
            raw = input("Selection: ").strip()
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except (ValueError, KeyboardInterrupt):
            print()
            sys.exit(0)
        print("  Invalid selection, try again.")


# ---------------------------------------------------------------------------
# Terraform helpers
# ---------------------------------------------------------------------------

def is_initialized(tf_dir: Path) -> bool:
    return (tf_dir / ".terraform").exists()


def run_init(tf_dir: Path, backend_config: Path) -> None:
    rel_backend = os.path.relpath(backend_config, tf_dir)
    cmd = ["terraform", "init", f"-backend-config={rel_backend}"]
    print(f"\n⚙️  terraform init has not been run here. Initialising...")
    print(f"   $ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=tf_dir)
    if result.returncode != 0:
        print("\n❌ terraform init failed.")
        sys.exit(result.returncode)
    print("\n✅ Init complete.")


# ---------------------------------------------------------------------------
# Variable parsing
# ---------------------------------------------------------------------------

def parse_variable_blocks(tf_dir: Path) -> dict[str, dict]:
    """
    Scan all .tf files for variable blocks.
    Returns {name: {"has_default": bool, "sensitive": bool}}.

    A variable with `default = null` is treated as unset — it is optional in
    Terraform but has no meaningful value, so we surface it for override.
    """
    block_re = re.compile(
        r'variable\s+"(\w+)"\s*\{((?:[^{}]|\{[^{}]*\})*)\}', re.DOTALL
    )
    variables: dict[str, dict] = {}
    for tf_file in sorted(tf_dir.glob("*.tf")):
        for match in block_re.finditer(tf_file.read_text()):
            name, body = match.group(1), match.group(2)
            default_match = re.search(r"\bdefault\s*=\s*(\S+)", body)
            has_real_default = bool(default_match) and default_match.group(1) != "null"
            variables[name] = {
                "has_default": has_real_default,
                "sensitive": bool(re.search(r"\bsensitive\s*=\s*true", body)),
            }
    return variables


def parse_tfvars_keys(tfvars_path: Path) -> set[str]:
    """Return the set of variable names assigned in a .tfvars file."""
    if not tfvars_path.exists():
        return set()
    keys = set()
    for line in tfvars_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Component selection
    components = find_components()
    if not components:
        print("❌ No components found under iac/components/")
        sys.exit(1)

    component = (
        components[0]
        if len(components) == 1
        else select(
            "Select a Terraform component:",
            components,
            display_fn=lambda c: c["name"],
        )
    )
    tf_dir: Path = component["tf_dir"]
    comp_name: str = component["name"]

    if len(components) == 1:
        print(f"\n✔ Component: {comp_name}")

    # 2. Environment selection
    envs = find_environments()
    if not envs:
        print("❌ No environments found under iac/environments/")
        sys.exit(1)

    env_cfg = select(
        "Select an environment:",
        envs,
        display_fn=lambda e: f"{e['env']}/{e['region']}",
    )
    config_dir: Path = env_cfg["config_dir"]

    backend_config = config_dir / f"{comp_name}.backend.hcl"
    tfvars = config_dir / f"{comp_name}.tfvars"

    for path, label in [(backend_config, "backend config"), (tfvars, "tfvars")]:
        if not path.exists():
            print(f"❌ {label} not found: {path}")
            sys.exit(1)

    # 3. Init if needed
    if not is_initialized(tf_dir):
        run_init(tf_dir, backend_config)
    else:
        print(f"✔ Already initialised")

    # 4. Prompt for every unset variable (no default, or default = null, not in tfvars)
    all_vars = parse_variable_blocks(tf_dir)
    set_vars = parse_tfvars_keys(tfvars)
    unset = {
        k: v
        for k, v in all_vars.items()
        if not v["has_default"] and k not in set_vars
    }

    extra_var_args: list[str] = []
    if unset:
        print(f"\nUnset variables (press Enter to leave unoverridden):")
        for var_name, meta in sorted(unset.items()):
            label = var_name + (" (sensitive)" if meta["sensitive"] else "")
            try:
                value = input(f"  {label}: ").strip()
            except KeyboardInterrupt:
                print()
                sys.exit(0)
            if value:
                extra_var_args.append(f"-var={var_name}={value}")

    # 5. Build command parts
    rel_tfvars = os.path.relpath(tfvars, tf_dir)
    plan_parts = ["terraform", "plan", f"-var-file={rel_tfvars}"] + extra_var_args
    apply_parts = ["terraform", "apply", f"-var-file={rel_tfvars}"] + extra_var_args

    plan_cmd = " \\\n    ".join(plan_parts)
    apply_cmd = " \\\n    ".join(apply_parts)

    divider = "─" * 60
    print(f"\n{divider}")
    print(f"📁  Directory: {tf_dir}")
    print(f"\n📋  Plan command:\n")
    print(f"    {plan_cmd}")
    print(f"\n🚀  To apply, first change to the terraform directory:\n")
    print(f"    cd {tf_dir}")
    print(f"\n    Then run:\n")
    print(f"    {apply_cmd}")
    print(f"{divider}\n")

    # 6. Optionally run the plan
    try:
        run_now = input("Run terraform plan now? [Y/n]: ").strip().lower()
    except KeyboardInterrupt:
        print()
        sys.exit(0)

    if run_now in ("", "y", "yes"):
        print()
        result = subprocess.run(plan_parts, cwd=tf_dir)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
