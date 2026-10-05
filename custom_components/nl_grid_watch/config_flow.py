"""Config flow for NL Grid Watch."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_POSTAL_CODE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    NAME,
)

POSTAL_RE = re.compile(r"^[1-9][0-9]{3}\s?[A-Z]{0,2}$")


def normalize_postal_code(value: str) -> str:
    """Return a Dutch postcode without spaces."""
    return re.sub(r"\s+", "", value).upper()


class NLGridWatchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NL Grid Watch."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the postcode and optional interruption credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            postal = normalize_postal_code(user_input[CONF_POSTAL_CODE])
            if not POSTAL_RE.match(postal) or len(postal) < 4:
                errors["base"] = "invalid_postal_code"
            else:
                await self.async_set_unique_id(postal)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{NAME} {postal}",
                    data={
                        CONF_POSTAL_CODE: postal,
                        CONF_CLIENT_ID: user_input.get(CONF_CLIENT_ID, ""),
                        CONF_CLIENT_SECRET: user_input.get(CONF_CLIENT_SECRET, ""),
                    },
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POSTAL_CODE): str,
                    vol.Optional(CONF_CLIENT_ID, default=""): str,
                    vol.Optional(CONF_CLIENT_SECRET, default=""): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NLGridWatchOptionsFlow:
        """Return the options flow."""
        return NLGridWatchOptionsFlow()


class NLGridWatchOptionsFlow(OptionsFlow):
    """Change scan interval and optional API credentials."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show options."""
        if user_input is not None:
            data = dict(self.config_entry.data)
            data[CONF_CLIENT_ID] = user_input.get(CONF_CLIENT_ID, "")
            data[CONF_CLIENT_SECRET] = user_input.get(CONF_CLIENT_SECRET, "")
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        data = self.config_entry.data
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=15, max=180)),
                    vol.Optional(
                        CONF_CLIENT_ID, default=data.get(CONF_CLIENT_ID, "")
                    ): str,
                    vol.Optional(
                        CONF_CLIENT_SECRET, default=data.get(CONF_CLIENT_SECRET, "")
                    ): str,
                }
            ),
        )
