"""
Skill executor — 2-layer skill system per ReckLabs Phase 1 architecture.

Layer 1 (Base): Encrypted .json.enc files in skills/base/ — platform-curated IP.
  Best-practice workflows, optimal API sequences, industry-specific defaults.
  AES-256 encrypted; only licensed MCP runtime can decrypt.

Layer 2 (Client): Plain .json files in skills/client/ — client customisation.
  API credentials, custom params, workflow overrides, business-specific values.
  Always readable and editable by the client.

At runtime: MCP server merges both layers. Client overrides apply on top of base.
Falls back to flat skills/*.json for backward compatibility.
"""
import json
import logging
from pathlib import Path

from config.settings import SKILLS_DIR, SKILLS_BASE_DIR, SKILLS_CLIENT_DIR

logger = logging.getLogger(__name__)


class SkillError(Exception):
    pass


class SkillExecutor:
    def __init__(self, tool_registry: dict):
        self._tools = tool_registry
        self._skills: dict[str, dict] = {}
        self._load_all()

    # ------------------------------------------------------------------
    # Layer loading
    # ------------------------------------------------------------------

    def _load_base_layer(self, name: str) -> dict | None:
        """Load base skill from skills/base/ — encrypted .enc preferred, plain .json fallback."""
        enc_path = SKILLS_BASE_DIR / f"{name}.json.enc"
        if enc_path.exists():
            try:
                from skills.skill_crypto import load_encrypted_skill
                return load_encrypted_skill(enc_path)
            except Exception as e:
                logger.error("Cannot decrypt base skill %s: %s", name, e)
                return None

        plain_path = SKILLS_BASE_DIR / f"{name}.json"
        if plain_path.exists():
            try:
                return json.loads(plain_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Cannot load base skill %s: %s", name, e)
        return None

    def _load_client_layer(self, name: str) -> dict:
        """Load client customisation layer from skills/client/."""
        path = SKILLS_CLIENT_DIR / f"{name}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Cannot load client skill layer %s: %s", name, e)
        return {}

    def _load_flat_skill(self, name: str) -> dict | None:
        """Backward-compatible flat skills/*.json loader."""
        path = SKILLS_DIR / f"{name}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Skip crypto module file
                if path.stem == "skill_crypto":
                    return None
                return data
            except Exception as e:
                logger.error("Cannot load flat skill %s: %s", name, e)
        return None

    # ------------------------------------------------------------------
    # Layer merging
    # ------------------------------------------------------------------

    def _merge_layers(self, base: dict, client: dict) -> dict:
        """
        Merge client customisation on top of the base skill.
        Client layer values override base defaults where specified.
        """
        if not client:
            return base

        merged = {k: v for k, v in base.items()}

        # Top-level metadata overrides
        for key in ("description", "llm_provider"):
            if key in client:
                merged[key] = client[key]

        # Step param overrides: {"params_override": {"step_name": {"param": value}}}
        client_overrides = client.get("params_override", {})
        if client_overrides:
            for step in merged.get("steps", []):
                sn = step.get("step_name", "")
                if sn in client_overrides:
                    step.setdefault("params", {}).update(client_overrides[sn])

        # Client context values (credentials, custom fields)
        if "context" in client:
            merged["client_context"] = client["context"]

        # Client can append additional steps after base steps
        if "additional_steps" in client:
            merged.setdefault("steps", []).extend(client["additional_steps"])

        return merged

    # ------------------------------------------------------------------
    # Skill loading
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        """Discover and load all skills from base/, client/, and flat skills/."""
        names: set[str] = set()

        if SKILLS_BASE_DIR.exists():
            for f in SKILLS_BASE_DIR.iterdir():
                if f.name.endswith(".json.enc"):
                    names.add(f.name[:-9])        # strip .json.enc
                elif f.suffix == ".json":
                    names.add(f.stem)

        if SKILLS_CLIENT_DIR.exists():
            for f in SKILLS_CLIENT_DIR.glob("*.json"):
                names.add(f.stem)

        if SKILLS_DIR.exists():
            for f in SKILLS_DIR.glob("*.json"):
                if f.stem != "skill_crypto":
                    names.add(f.stem)

        for name in names:
            self._load_skill(name)

    def _load_skill(self, name: str) -> None:
        """Load one skill by merging base + client layers."""
        base = self._load_base_layer(name)

        if base is None:
            base = self._load_flat_skill(name)

        if base is None:
            # Client-only skill — treat client layer as the full definition
            client = self._load_client_layer(name)
            if client and "steps" in client:
                skill_name = client.get("name", name)
                self._skills[skill_name] = client
                logger.info("Loaded client-only skill: %s", skill_name)
            return

        client = self._load_client_layer(name)
        merged = self._merge_layers(base, client)
        skill_name = merged.get("name", name)
        self._skills[skill_name] = merged
        logger.info(
            "Loaded skill '%s'  base=yes  client=%s",
            skill_name, "yes" if client else "no",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self) -> list[str]:
        """Reload all skill files from disk."""
        self._skills.clear()
        self._load_all()
        return list(self._skills.keys())

    def list_skills(self) -> list[dict]:
        return [
            {
                "name": s.get("name", n),
                "description": s.get("description", ""),
                "version": s.get("version", "1.0"),
                "connector": s.get("connector", ""),
                "llm_provider": s.get("llm_provider", "claude"),
                "supports": s.get("supports", ["text"]),
                "steps": len(s.get("steps", [])),
            }
            for n, s in self._skills.items()
        ]

    def get_skill(self, name: str) -> dict:
        if name not in self._skills:
            raise SkillError(
                f"Skill '{name}' not found. Available: {list(self._skills)}"
            )
        return self._skills[name]

    def execute_skill(self, name: str, context: dict = None) -> dict:
        """
        Execute a skill by name.
        context: optional dict of values to substitute into step params.
        """
        skill = self.get_skill(name)
        steps = skill.get("steps", [])

        # Merge client_context (from skill layer) with caller-supplied context
        exec_context = dict(context or {})
        exec_context.update(skill.get("client_context", {}))

        results = {}
        step_outputs = {}

        logger.info("Executing skill '%s' (%d steps)", name, len(steps))

        for i, step in enumerate(steps):
            step_name = step.get("step_name", f"step_{i + 1}")
            tool_name = step.get("tool")
            raw_params = step.get("params", {})

            if not tool_name:
                raise SkillError(f"Step '{step_name}' missing 'tool'")

            params = self._resolve_params(raw_params, step_outputs, exec_context)

            if tool_name not in self._tools:
                raise SkillError(
                    f"Step '{step_name}' references unknown tool '{tool_name}'. "
                    f"Available: {list(self._tools)}"
                )

            try:
                logger.debug("Step '%s' → tool '%s'", step_name, tool_name)
                output = self._tools[tool_name](params)
                results[step_name] = {"status": "ok", "output": output}
                step_outputs[step_name] = output
            except Exception as e:
                results[step_name] = {"status": "error", "error": str(e)}
                if step.get("on_error") != "continue":
                    raise SkillError(
                        f"Skill '{name}' failed at step '{step_name}': {e}"
                    ) from e

        return {
            "skill": name,
            "status": "completed",
            "steps_run": len(steps),
            "results": results,
        }

    def _resolve_params(self, params: dict, step_outputs: dict, context: dict) -> dict:
        """Replace {{step_name.field}} and {{context.key}} templates in params."""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                ref = v[2:-2].strip()
                parts = ref.split(".", 1)
                source = parts[0]
                field = parts[1] if len(parts) > 1 else None
                if source == "context":
                    resolved[k] = context.get(field, v)
                elif source in step_outputs:
                    data = step_outputs[source]
                    resolved[k] = (
                        data.get(field, v) if isinstance(data, dict) and field else data
                    )
                else:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved
