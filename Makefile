# HAKIM — convenience targets
SHELL := /bin/bash
ROOT  := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Fire a Morning Brief right now. Reads NTFY_URL from the loaded launchd agent's
# env if present, else from your shell env. Delivers to your phone when NTFY_URL is set.
.PHONY: brief
brief:
	@NTFY_URL="$${NTFY_URL:-$$(/bin/launchctl getenv NTFY_URL 2>/dev/null)}" \
	  python3 "$(ROOT)scripts/morning_brief.py"

# Compose and print the whisper without sending (safe preview).
.PHONY: brief-dry
brief-dry:
	@python3 "$(ROOT)scripts/morning_brief.py" --dry

# Record today's zakatable total + nisab crossing (the hawl trail). Idempotent per day.
.PHONY: hawl
hawl:
	@python3 "$(ROOT)scripts/hawl_track.py"

# Preview the hawl snapshot POST without sending.
.PHONY: hawl-dry
hawl-dry:
	@python3 "$(ROOT)scripts/hawl_track.py" --dry

# Load / reload the nightly (23:50) hawl launchd agent.
.PHONY: hawl-install
hawl-install:
	@launchctl unload "$(HOME)/Library/LaunchAgents/com.hakim.hawl.plist" 2>/dev/null || true
	@cp "$(ROOT)launchd/com.hakim.hawl.plist" "$(HOME)/Library/LaunchAgents/"
	@launchctl load "$(HOME)/Library/LaunchAgents/com.hakim.hawl.plist"
	@echo "loaded com.hakim.hawl (23:50 daily)"
	@launchctl list | grep hakim.hawl || true

# Export the full ledger → CSV (detail) + PDF (summary) in ~/Documents/Hakim/exports/.
.PHONY: export
export:
	@python3 "$(ROOT)scripts/export_ledger.py"

# Load / reload the 07:00 launchd agent.
.PHONY: brief-install
brief-install:
	@launchctl unload "$(HOME)/Library/LaunchAgents/com.hakim.morningbrief.plist" 2>/dev/null || true
	@cp "$(ROOT)launchd/com.hakim.morningbrief.plist" "$(HOME)/Library/LaunchAgents/"
	@launchctl load "$(HOME)/Library/LaunchAgents/com.hakim.morningbrief.plist"
	@echo "loaded com.hakim.morningbrief (07:00 daily)"
	@launchctl list | grep hakim.morningbrief || true
