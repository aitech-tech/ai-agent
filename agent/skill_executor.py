"""
Skill executor — 2-layer skill system per ReckLabs Phase 1 architecture.

Layer 1 (Base): Encrypted .json.enc files in skills/base/<connector>/ — platform-curated IP.
  Best-practice workflows, optimal API sequences, industry-specific defaults.
  AES-256 encrypted; only licensed MCP runtime can decrypt.

Layer 2 (Client): Plain .json files in skills/client/<connector>/ — client customisation.
  API credentials, custom params, workflow overrides, business-specific values.
  Always readable and editable by the client.

At runtime: MCP server merges both layers (namespaced: connector.skill_name).
Flat skills/*.json loading is disabled by default; enable with:
  RECKLABS_ENABLE_LEGACY_FLAT_SKILLS=1

Step types:
  "tool"      (default) — calls a registered MCP tool by name
  "transform" — pure Python aggregation/merge on prior step outputs; no external calls
  LLM reasoning is handled entirely by Claude Desktop, not this executor.
"""
import json
import logging
import os

from config.settings import SKILLS_DIR, SKILLS_BASE_DIR, SKILLS_CLIENT_DIR

logger = logging.getLogger(__name__)

INTENT_MAP_FILE = SKILLS_DIR / "intent_map.json"
RESERVED_SKILL_FILES = {"intent_map", "skill_versions"}


class SkillError(Exception):
    pass


class SkillExecutor:
    def __init__(self, tool_registry: dict):
        self._tools = tool_registry
        self._skills: dict[str, dict] = {}
        self._intent_map: dict[str, str] = {}
        self._load_all()
        self._load_intent_map()

    # ------------------------------------------------------------------
    # Intent map
    # ------------------------------------------------------------------

    def _load_intent_map(self) -> None:
        if INTENT_MAP_FILE.exists():
            try:
                data = json.loads(INTENT_MAP_FILE.read_text(encoding="utf-8"))
                self._intent_map = data.get("mappings", {})
                logger.info("Loaded intent map: %d patterns", len(self._intent_map))
            except Exception as e:
                logger.error("Cannot load intent_map.json: %s", e)

    def resolve_intent(self, query: str) -> str | None:
        """
        Map a natural language query to a skill name.
        Tries exact match first, then substring containment (longest key wins).
        Returns skill name or None if no match.
        """
        q = query.lower().strip()
        if q in self._intent_map:
            return self._intent_map[q]
        matches = [(k, v) for k, v in self._intent_map.items() if k in q]
        if matches:
            best = max(matches, key=lambda x: len(x[0]))
            return best[1]
        return None

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
                if path.stem in RESERVED_SKILL_FILES:
                    return None
                return data
            except Exception as e:
                logger.error("Cannot load flat skill %s: %s", name, e)
        return None

    # ------------------------------------------------------------------
    # Layer merging
    # ------------------------------------------------------------------

    def _merge_layers(self, base: dict, client: dict) -> dict:
        """Merge client customisation on top of the base skill."""
        if not client:
            return base

        merged = {k: v for k, v in base.items()}

        for key in ("description", "llm_provider"):
            if key in client:
                merged[key] = client[key]

        client_overrides = client.get("params_override", {})
        if client_overrides:
            for step in merged.get("steps", []):
                sn = step.get("step_name", "")
                if sn in client_overrides:
                    step.setdefault("params", {}).update(client_overrides[sn])

        if "context" in client:
            merged["client_context"] = client["context"]

        if "additional_steps" in client:
            merged.setdefault("steps", []).extend(client["additional_steps"])

        return merged

    # ------------------------------------------------------------------
    # Skill loading
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        # Primary: namespaced connector skills — skills/base/<connector>/*.json[.enc]
        if SKILLS_BASE_DIR.exists():
            for connector_dir in SKILLS_BASE_DIR.iterdir():
                if connector_dir.is_dir():
                    connector_name = connector_dir.name
                    connector_names: set[str] = set()
                    for f in connector_dir.iterdir():
                        if f.is_file():
                            if f.name.endswith(".json.enc"):
                                connector_names.add(f.name[:-9])
                            elif f.suffix == ".json" and f.stem not in RESERVED_SKILL_FILES:
                                connector_names.add(f.stem)
                    for skill_name in connector_names:
                        self._load_connector_skill(connector_name, skill_name)

        # Client-only connector skills — skills/client/<connector>/*.json.
        # These are generated from user-edited Word templates and run as connector.skill_id.
        if SKILLS_CLIENT_DIR.exists():
            for connector_dir in SKILLS_CLIENT_DIR.iterdir():
                if not connector_dir.is_dir():
                    continue
                connector_name = connector_dir.name
                for f in connector_dir.glob("*.json"):
                    if f.stem not in RESERVED_SKILL_FILES:
                        self._load_connector_skill(connector_name, f.stem)

        # Legacy flat skill loading — disabled by default.
        # Enable with env var: RECKLABS_ENABLE_LEGACY_FLAT_SKILLS=1
        if os.environ.get("RECKLABS_ENABLE_LEGACY_FLAT_SKILLS") == "1":
            logger.warning("Legacy flat skill loading enabled (RECKLABS_ENABLE_LEGACY_FLAT_SKILLS=1)")
            names: set[str] = set()

            if SKILLS_BASE_DIR.exists():
                for f in SKILLS_BASE_DIR.iterdir():
                    if f.is_file():
                        if f.name.endswith(".json.enc"):
                            names.add(f.name[:-9])
                        elif f.suffix == ".json" and f.stem not in RESERVED_SKILL_FILES:
                            names.add(f.stem)

            if SKILLS_CLIENT_DIR.exists():
                for f in SKILLS_CLIENT_DIR.glob("*.json"):
                    if f.stem not in RESERVED_SKILL_FILES:
                        names.add(f.stem)

            if SKILLS_DIR.exists():
                for f in SKILLS_DIR.glob("*.json"):
                    if f.stem not in RESERVED_SKILL_FILES:
                        names.add(f.stem)

            for name in names:
                self._load_skill(name)

    def _load_connector_skill(self, connector_name: str, skill_name: str) -> None:
        """Load a skill from a connector subfolder, namespaced as connector.skill_name."""
        base_dir = SKILLS_BASE_DIR / connector_name
        client_dir = SKILLS_CLIENT_DIR / connector_name

        # Load base
        base = None
        enc_path = base_dir / f"{skill_name}.json.enc"
        if enc_path.exists():
            try:
                from skills.skill_crypto import load_encrypted_skill
                base = load_encrypted_skill(enc_path)
            except Exception as e:
                logger.error("Cannot decrypt %s/%s: %s", connector_name, skill_name, e)
                return
        else:
            plain_path = base_dir / f"{skill_name}.json"
            if plain_path.exists():
                try:
                    base = json.loads(plain_path.read_text(encoding="utf-8"))
                except Exception as e:
                    logger.error("Cannot load %s/%s: %s", connector_name, skill_name, e)
                    return

        # Load client override or client-only skill
        client = {}
        client_path = client_dir / f"{skill_name}.json" if client_dir.exists() else None
        if client_path and client_path.exists():
            try:
                client = json.loads(client_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Cannot load client skill %s/%s: %s", connector_name, skill_name, e)

        if base is None and not client:
            return

        if base is None:
            merged = dict(client)
            merged.setdefault("connector", connector_name)
        else:
            merged = self._merge_layers(base, client)

        namespaced_name = f"{connector_name}.{skill_name}"
        self._skills[namespaced_name] = merged
        logger.info("Loaded connector skill: %s", namespaced_name)

    def _load_skill(self, name: str) -> None:
        base = self._load_base_layer(name)

        if base is None:
            base = self._load_flat_skill(name)

        if base is None:
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
        self._skills.clear()
        self._intent_map.clear()
        self._load_all()
        self._load_intent_map()
        return list(self._skills.keys())

    def list_skills(self) -> list[dict]:
        out = []
        for n, s in self._skills.items():
            # n is the registry key — always the executable ID (namespaced if connector skill)
            # display_name: human title without connector prefix
            raw_name = s.get("name", n)
            display_name = raw_name.split(".")[-1].replace("_", " ").title() if "." in n else raw_name
            # connector: from skill data or inferred from namespaced key
            connector = s.get("connector", n.split(".")[0] if "." in n else "")
            out.append({
                "id": n,
                "name": n,
                "display_name": display_name,
                "description": s.get("description", ""),
                "version": s.get("version", "1.0"),
                "connector": connector,
                "llm_provider": s.get("llm_provider", "claude"),
                "supports": s.get("supports", ["text"]),
                "steps": len(s.get("steps", [])),
            })
        return out

    def get_skill(self, name: str) -> dict:
        if name not in self._skills:
            available = list(self._skills.keys())
            raise SkillError(
                f"Skill '{name}' not found. Available skill IDs: {available}"
            )
        return self._skills[name]

    def execute_skill(self, name: str, context: dict = None) -> dict:
        """
        Execute a skill by name.
        Supports step types: "tool" (default) and "transform".
        context: optional dict of values to substitute into step params.
        """
        skill = self.get_skill(name)
        steps = skill.get("steps", [])

        exec_context = dict(context or {})
        exec_context.update(skill.get("client_context", {}))

        results = {}
        step_outputs = {}

        logger.info("Executing skill '%s' (%d steps)", name, len(steps))

        for i, step in enumerate(steps):
            step_name = step.get("step_name", f"step_{i + 1}")
            step_type = step.get("type", "tool")
            on_error = step.get("on_error", "stop")

            try:
                if step_type == "transform":
                    output = self._execute_transform_step(step, step_name, step_outputs)
                else:
                    output = self._execute_tool_step(step, step_name, step_outputs, exec_context)

                # Treat explicit success:false from the tool as a step failure
                if isinstance(output, dict) and output.get("success") is False:
                    err_msg = output.get("error", "tool_failure")
                    results[step_name] = {"status": "error", "output": output}
                    step_outputs[step_name] = output
                    logger.warning("Skill '%s' step '%s' tool returned success:false — %s", name, step_name, err_msg)
                    if on_error != "continue":
                        raise SkillError(
                            f"Skill '{name}' failed at step '{step_name}': {err_msg}"
                        )
                    continue

                results[step_name] = {"status": "ok", "output": output}
                step_outputs[step_name] = output

            except SkillError:
                raise
            except Exception as e:
                results[step_name] = {"status": "error", "error": str(e)}
                logger.error("Skill '%s' step '%s' failed: %s", name, step_name, e)
                if on_error != "continue":
                    raise SkillError(
                        f"Skill '{name}' failed at step '{step_name}': {e}"
                    ) from e

        final_output = self._build_final_output(name, steps, results, step_outputs)

        return {
            "skill": name,
            "status": "completed",
            "steps_run": len(steps),
            "results": results,
            "output": final_output,
        }

    # ------------------------------------------------------------------
    # Step executors
    # ------------------------------------------------------------------

    def _execute_tool_step(
        self, step: dict, step_name: str, step_outputs: dict, exec_context: dict
    ) -> dict:
        tool_name = step.get("tool")
        raw_params = step.get("params", {})

        if not tool_name:
            raise SkillError(f"Tool step '{step_name}' missing 'tool' field")
        if tool_name not in self._tools:
            raise SkillError(
                f"Step '{step_name}' references unknown tool '{tool_name}'. "
                f"Available: {list(self._tools)}"
            )

        params = self._resolve_params(raw_params, step_outputs, exec_context)
        logger.debug("Tool step '%s' -> '%s'", step_name, tool_name)
        return self._tools[tool_name](params)

    def _execute_transform_step(
        self, step: dict, step_name: str, step_outputs: dict
    ) -> dict:
        """Pure Python aggregation/merge — no external API calls."""
        operation = step.get("operation", "aggregate")
        if operation == "aggregate":
            return self._transform_aggregate(step, step_outputs)
        if operation == "merge":
            return self._transform_merge(step, step_outputs)
        raise SkillError(f"Transform step '{step_name}' has unknown operation: '{operation}'")

    def _transform_aggregate(self, step: dict, step_outputs: dict) -> dict:
        """Count records and group by specified fields from one input step."""
        input_step = step.get("input_step")
        raw = step_outputs.get(input_step, {})
        records = raw.get("data", raw) if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            records = []

        result: dict = {"total": len(records)}

        for field in step.get("group_by", []):
            counts: dict = {}
            for r in records:
                if isinstance(r, dict):
                    key = str(r.get(field) or "Unknown")
                    counts[key] = counts.get(key, 0) + 1
            if counts:
                result[f"by_{field.lower()}"] = counts

        # Data completeness: flag percentage of records missing each key field
        completeness_fields = step.get("completeness_fields", [])
        if completeness_fields and records:
            completeness: dict = {}
            for field in completeness_fields:
                filled = sum(1 for r in records if isinstance(r, dict) and r.get(field))
                completeness[field] = round(filled / len(records) * 100)
            result["completeness_pct"] = completeness

        logger.debug("Transform aggregate: %s", result)
        return result

    def _transform_merge(self, step: dict, step_outputs: dict) -> dict:
        """Combine record counts from multiple input steps into a totals summary."""
        input_steps = step.get("input_steps", {})
        totals: dict = {}

        if isinstance(input_steps, dict):
            for label, src in input_steps.items():
                raw = step_outputs.get(src, {})
                records = raw.get("data", raw) if isinstance(raw, dict) else raw
                totals[label] = len(records) if isinstance(records, list) else 0

        logger.debug("Transform merge totals: %s", totals)
        return {"totals": totals}

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    def _build_final_output(
        self, skill_name: str, steps: list, results: dict, step_outputs: dict
    ) -> dict:
        """
        Separate tool step records (data) from transform step aggregations (summary)
        into a clean structured output for Claude Desktop to reason over.
        """
        data_steps: dict = {}
        summary: dict = {}

        for step in steps:
            sn = step.get("step_name", "")
            st = step.get("type", "tool")
            if sn not in results or results[sn]["status"] == "error":
                continue
            raw = step_outputs.get(sn)
            if st == "transform":
                summary[sn] = raw
            else:
                if isinstance(raw, dict) and "data" in raw:
                    data_steps[sn] = raw["data"]
                else:
                    data_steps[sn] = raw

        out: dict = {"skill": skill_name, "data": data_steps}
        if summary:
            out["summary"] = summary
        return out

    # ------------------------------------------------------------------
    # Param resolution
    # ------------------------------------------------------------------

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
